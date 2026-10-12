import { useEffect, useRef, useState } from 'react';
import { ApiError, approveRubric, draftRubric, evaluateResume, extractPdf, getRubric, listRubrics } from './api';
import type { ApprovedRubric, Criteria, Draft, Evaluation, ProviderOutcome, Question, RubricSummary } from './types';

type Step = 'rubric' | 'resume' | 'compare';

const blankDraft = (): Draft => ({ role: '', creation_source: 'manual', questions: [] });

function newQuestion(type: Question['type']): Question {
  const criteria: Criteria = type === 'choice'
    ? { documented: 'The resume documents this evidence.', insufficient: 'The evidence is not documented.' }
    : type === 'score'
      ? ['No documented evidence', 'Some documented evidence', 'Strong documented evidence']
      : { false: 'The proposition is not documented.', true: 'The proposition is documented.' };
  return { id: `question_${crypto.randomUUID().slice(0, 8)}`, domain: '', instructions: '', type, criteria };
}

export function App() {
  const [step, setStep] = useState<Step>('rubric');
  const [draft, setDraft] = useState<Draft>(blankDraft);
  const [creationMode, setCreationMode] = useState<'manual' | 'assisted'>('manual');
  const [jobDescription, setJobDescription] = useState('');
  const [rubrics, setRubrics] = useState<RubricSummary[]>([]);
  const [approved, setApproved] = useState<ApprovedRubric | null>(null);
  const [resumeText, setResumeText] = useState('');
  const [resumeName, setResumeName] = useState('');
  const [reviewed, setReviewed] = useState(false);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const uploadGeneration = useRef(0);
  const evaluationGeneration = useRef(0);

  const refresh = () => listRubrics().then(setRubrics).catch(() => setMessage('Could not load rubrics.'));
  useEffect(() => { void refresh(); }, []);

  const clearCandidate = () => {
    uploadGeneration.current += 1;
    setResumeName('');
    setResumeText('');
    setReviewed(false);
    evaluationGeneration.current += 1;
    setEvaluation(null);
  };

  const updateQuestion = (index: number, next: Question) => setDraft((current) => ({
    ...current,
    questions: current.questions.map((question, position) => position === index ? next : question),
  }));

  const load = async (id: string, version: number) => {
    setBusy(true);
    setMessage('');
    try {
      const rubric = await getRubric(id, version);
      setApproved(rubric);
      setCreationMode('manual');
      setDraft({ role: rubric.role, questions: rubric.questions, creation_source: 'revision', base_version: { id: rubric.id, version: rubric.version } });
      clearCandidate();
      setMessage(`Version ${version} selected. Edit it to create a revision, or continue with this version.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Could not load the rubric.');
    } finally {
      setBusy(false);
    }
  };

  const approve = async () => {
    setBusy(true);
    setMessage('');
    try {
      const result = await approveRubric(draft);
      setApproved(result);
      setDraft({ role: result.role, questions: result.questions, creation_source: 'revision', base_version: { id: result.id, version: result.version } });
      clearCandidate();
      setMessage(`Approved ${result.role}, version ${result.version}.`);
      await refresh();
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : 'Could not approve the rubric.');
    } finally {
      setBusy(false);
    }
  };

  const upload = async (file?: File) => {
    clearCandidate();
    setMessage('');
    if (!file) return;
    const generation = uploadGeneration.current;
    setResumeName(file.name);
    setBusy(true);
    try {
      const result = await extractPdf(file);
      if (generation === uploadGeneration.current) {
        setResumeText(result.text);
        setMessage('Text extracted. Review and edit it before continuing.');
      }
    } catch (error) {
      if (generation === uploadGeneration.current) setMessage(error instanceof ApiError ? error.message : 'Could not extract the PDF.');
    } finally {
      if (generation === uploadGeneration.current) setBusy(false);
    }
  };

  const generateDraft = async () => {
    if (!draft.role.trim() || !jobDescription.trim()) return;
    setBusy(true);
    setMessage('');
    try {
      const result = await draftRubric(draft.role, jobDescription);
      setDraft(result);
      setApproved(null);
      clearCandidate();
      setMessage('Draft generated. Review every question before approval.');
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : 'Could not generate the rubric draft.');
    } finally {
      setBusy(false);
    }
  };

  const evaluate = async () => {
    if (!approved || !reviewed || !resumeText.trim()) return;
    evaluationGeneration.current += 1;
    const generation = evaluationGeneration.current;
    setEvaluation(null);
    setMessage('');
    setBusy(true);
    try {
      const result = await evaluateResume({ id: approved.id, version: approved.version }, resumeText);
      if (generation === evaluationGeneration.current) setEvaluation(result);
    } catch (error) {
      if (generation === evaluationGeneration.current) setMessage(error instanceof ApiError ? error.message : 'Could not run the comparison.');
    } finally {
      if (generation === evaluationGeneration.current) setBusy(false);
    }
  };

  return <main>
    <header className="hero"><p className="eyebrow">Recruiter pilot</p><h1>Make the rubric explicit before reviewing candidates.</h1><p>Every evaluation uses an approved, immutable rubric version.</p></header>
    <nav aria-label="Workflow" className="steps">
      {([['rubric', 'Rubric'], ['resume', 'Resume review'], ['compare', 'Compare']] as const).map(([value, label], index) => <button className="step-link" disabled={(value !== 'rubric' && !approved) || (value === 'compare' && !reviewed)} aria-current={step === value ? 'step' : undefined} key={value} onClick={() => setStep(value)}><b>{index + 1}</b> {label}</button>)}
    </nav>

    {step === 'rubric' && <div className="layout">
      <aside aria-label="Approved rubrics">
        <div className="section-heading"><div><p className="eyebrow">Library</p><h2>Approved rubrics</h2></div><button className="secondary" onClick={() => { setDraft(blankDraft()); setCreationMode('manual'); setJobDescription(''); setApproved(null); clearCandidate(); setMessage(''); }}>New</button></div>
        {rubrics.length === 0 ? <p className="muted">No approved rubrics yet.</p> : rubrics.map((rubric) => <section className="rubric-summary" key={rubric.id}><h3>{rubric.role}</h3><div className="version-list">{rubric.versions.map((version) => <button className="version" disabled={busy} key={version.version} onClick={() => load(rubric.id, version.version)}>v{version.version} <small>{new Date(version.created_at).toLocaleDateString()}</small></button>)}</div></section>)}
      </aside>
      <section className="workspace" aria-labelledby="editor-title">
        <div className="section-heading"><div><p className="eyebrow">{draft.base_version ? `Revision of v${draft.base_version.version}` : 'Manual draft'}</p><h2 id="editor-title">Rubric editor</h2></div>{approved && <span className="badge">Selected: v{approved.version}</span>}</div>
        {!draft.base_version && <div className="mode-tabs" aria-label="Rubric creation mode"><button className={creationMode === 'manual' ? 'active' : 'secondary'} onClick={() => { setCreationMode('manual'); setDraft({ ...blankDraft(), role: draft.role }); }}>Manual</button><button className={creationMode === 'assisted' ? 'active' : 'secondary'} onClick={() => { setCreationMode('assisted'); setDraft({ ...blankDraft(), role: draft.role, creation_source: 'assisted' }); }}>Assisted</button></div>}
        <label>Role<input value={draft.role} onChange={(event) => setDraft({ ...draft, role: event.target.value })} placeholder="e.g. Backend engineer" /></label>
        {!draft.base_version && creationMode === 'assisted' && <div className="assisted"><label>Job description<textarea rows={8} value={jobDescription} onChange={(event) => setJobDescription(event.target.value)} placeholder="Paste the job description. It is sent only to your configured drafting endpoint and is not saved by Rubric." /></label><button disabled={busy || !draft.role.trim() || !jobDescription.trim()} onClick={generateDraft}>{busy ? 'Generating...' : 'Generate questions'}</button></div>}
        <div className="questions">{draft.questions.map((question, index) => <QuestionEditor index={index} key={question.id} question={question} update={(next) => updateQuestion(index, next)} remove={() => setDraft({ ...draft, questions: draft.questions.filter((_, position) => position !== index) })} />)}</div>
        <div className="add-row" aria-label="Add a question"><span>Add question</span>{(['choice', 'score', 'noul'] as const).map((type) => <button className="secondary" key={type} onClick={() => setDraft({ ...draft, questions: [...draft.questions, newQuestion(type)] })}>{type === 'noul' ? 'Yes / no' : type[0].toUpperCase() + type.slice(1)}</button>)}</div>
        {message && <p className="notice" role="status">{message}</p>}
        <div className="actions"><p className="muted">Approval creates a permanent version. Later edits become a new version.</p>{approved && <button className="secondary" onClick={() => setStep('resume')}>Use selected version</button>}<button disabled={busy || !draft.role.trim() || draft.questions.length === 0} onClick={approve}>{busy ? 'Working...' : draft.base_version ? 'Approve new version' : 'Approve rubric'}</button></div>
      </section>
    </div>}

    {step === 'resume' && approved && <section className="workspace single" aria-labelledby="resume-title">
      <div className="section-heading"><div><p className="eyebrow">{approved.role} / v{approved.version}</p><h2 id="resume-title">Review resume text</h2></div><button className="secondary" onClick={clearCandidate}>Clear candidate</button></div>
      <p className="muted">Upload one text-based PDF up to 10 MB. The file and extracted text stay in memory and are not saved by Rubric.</p>
      <label className="upload">Resume PDF<input type="file" accept="application/pdf,.pdf" disabled={busy} onChange={(event) => { void upload(event.currentTarget.files?.[0]); event.currentTarget.value = ''; }} /></label>
      {resumeName && <p className="file-name">{busy ? 'Extracting' : 'Loaded'}: {resumeName}</p>}
      {resumeText && <label>Extracted text<textarea className="resume-text" rows={18} value={resumeText} onChange={(event) => { setResumeText(event.target.value); setReviewed(false); evaluationGeneration.current += 1; setEvaluation(null); }} /></label>}
      {resumeText && <label className="check"><input type="checkbox" checked={reviewed} onChange={(event) => setReviewed(event.target.checked)} /> I reviewed this text and it represents the resume.</label>}
      {message && <p className="notice" role="status">{message}</p>}
      <div className="actions"><button className="secondary" onClick={() => setStep('rubric')}>Back</button><button disabled={!reviewed || !resumeText.trim()} onClick={() => setStep('compare')}>Continue to comparison</button></div>
    </section>}

    {step === 'compare' && approved && <section className="workspace single"><p className="eyebrow">{approved.role} / v{approved.version}</p><h2>Provider comparison</h2><p className="privacy-note">Running this comparison sends the reviewed text and rubric questions to Typesafe's Jev API and Boundless's Laya endpoint. Their account terms govern retention and processing.</p>{!evaluation && <div className="empty-results"><p>Both providers evaluate the same text and questions. A failure from one does not hide the other result.</p><button disabled={busy} onClick={evaluate}>{busy ? 'Evaluating...' : 'Run comparison'}</button></div>}{evaluation && <div className="results"><OutcomeCard name="Jev" outcome={evaluation.jev} rubric={approved} /><OutcomeCard name="Laya on Boundless" outcome={evaluation.laya} rubric={approved} /></div>}{message && <p className="notice" role="status">{message}</p>}<div className="actions"><button className="secondary" onClick={() => setStep('resume')}>Back to text review</button>{evaluation && <button onClick={evaluate} disabled={busy}>Run again</button>}</div></section>}
  </main>;
}

function OutcomeCard({ name, outcome, rubric }: { name: string; outcome: ProviderOutcome; rubric: ApprovedRubric }) {
  return <article className="outcome"><div className="section-heading"><div><p className="eyebrow">{outcome.backend}</p><h3>{name}</h3></div><span className={`status ${outcome.status}`}>{outcome.status}</span></div><p className="provider-meta">{outcome.served_model || outcome.model} / {outcome.elapsed_ms} ms</p>{outcome.status === 'error' ? <p className="provider-error">{outcome.error?.message || 'The provider failed.'}</p> : rubric.questions.map((question) => { const answer = outcome.answers?.[question.id]; return <section className="answer" key={question.id}><p className="domain">{question.domain}</p><h4>{question.instructions}</h4><p className="decision">{formatAnswer(answer)}</p>{typeof answer?.confidence === 'number' && <p>Provider confidence: {(answer.confidence * 100).toFixed(1)}%</p>}{typeof answer?.probabilities === 'object' && answer.probabilities !== null && <dl>{Object.entries(answer.probabilities as Record<string, number>).map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{(value * 100).toFixed(1)}%</dd></div>)}</dl>}</section>; })}</article>;
}

function formatAnswer(answer?: Record<string, unknown>): string {
  if (!answer) return 'Missing answer';
  if (answer.type === 'choice') return String(answer.choice);
  if (answer.type === 'score' && typeof answer.score === 'number') return answer.score.toFixed(2);
  if (answer.type === 'noul' && typeof answer.noul === 'number') return `${(answer.noul * 100).toFixed(1)}% yes`;
  return 'Invalid answer';
}

function QuestionEditor({ index, question, update, remove }: { index: number; question: Question; update: (question: Question) => void; remove: () => void }) {
  const changeType = (type: Question['type']) => update({ ...newQuestion(type), id: question.id, domain: question.domain, instructions: question.instructions });
  return <fieldset className="question-card"><legend>Question {index + 1}</legend><div className="question-grid"><label>Domain<input value={question.domain} onChange={(event) => update({ ...question, domain: event.target.value })} /></label><label>Answer type<select value={question.type} onChange={(event) => changeType(event.target.value as Question['type'])}><option value="choice">Choice</option><option value="score">Score</option><option value="noul">Yes / no</option></select></label></div><label>Instructions<textarea rows={2} value={question.instructions} onChange={(event) => update({ ...question, instructions: event.target.value })} placeholder="Ask about evidence documented in the resume." /></label><CriteriaEditor question={question} update={update} /><div className="question-footer"><code>{question.id}</code><button className="danger" onClick={remove}>Remove</button></div></fieldset>;
}

function CriteriaEditor({ question, update }: { question: Question; update: (question: Question) => void }) {
  if (question.type === 'score') {
    const levels = question.criteria as string[];
    return <div className="criteria"><span>Ordered levels</span>{levels.map((level, index) => <div className="criterion" key={index}><b>{index}</b><input value={level} onChange={(event) => update({ ...question, criteria: levels.map((item, position) => position === index ? event.target.value : item) })} /><button className="icon" aria-label={`Remove level ${index + 1}`} disabled={levels.length <= 2} onClick={() => update({ ...question, criteria: levels.filter((_, position) => position !== index) })}>x</button></div>)}<button className="secondary" disabled={levels.length >= 10} onClick={() => update({ ...question, criteria: [...levels, ''] })}>Add level</button></div>;
  }
  const criteria = question.criteria as Record<string, string>;
  const entries = Object.entries(criteria);
  const fixed = question.type === 'noul';
  return <div className="criteria"><span>{fixed ? 'Yes / no meaning' : 'Choices'}</span>{entries.map(([label, description], index) => <div className="criterion" key={`${label}-${index}`}><input aria-label="Label" disabled={fixed} value={label} onChange={(event) => update({ ...question, criteria: Object.fromEntries(entries.map((entry, position) => position === index ? [event.target.value, entry[1]] : entry)) })} /><input aria-label={`${label} description`} value={description} onChange={(event) => update({ ...question, criteria: Object.fromEntries(entries.map((entry, position) => position === index ? [entry[0], event.target.value] : entry)) })} />{!fixed && <button className="icon" aria-label={`Remove ${label}`} disabled={entries.length <= 2} onClick={() => update({ ...question, criteria: Object.fromEntries(entries.filter((_, position) => position !== index)) })}>x</button>}</div>)}{!fixed && <button className="secondary" disabled={entries.length >= 255} onClick={() => update({ ...question, criteria: { ...criteria, [`option_${entries.length + 1}`]: '' } })}>Add choice</button>}</div>;
}
