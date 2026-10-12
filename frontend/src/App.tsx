import { useEffect, useState } from 'react';
import { ApiError, approveRubric, getRubric, listRubrics } from './api';
import type { ApprovedRubric, Criteria, Draft, Question, RubricSummary } from './types';

const blankDraft = (): Draft => ({ role: '', creation_source: 'manual', questions: [] });

function newQuestion(type: Question['type']): Question {
  const criteria: Criteria =
    type === 'choice'
      ? { documented: 'The resume documents this evidence.', insufficient: 'The evidence is not documented.' }
      : type === 'score'
        ? ['No documented evidence', 'Some documented evidence', 'Strong documented evidence']
        : { false: 'The proposition is not documented.', true: 'The proposition is documented.' };
  return {
    id: `question_${crypto.randomUUID().slice(0, 8)}`,
    domain: '',
    instructions: '',
    type,
    criteria,
  };
}

export function App() {
  const [draft, setDraft] = useState<Draft>(blankDraft);
  const [rubrics, setRubrics] = useState<RubricSummary[]>([]);
  const [approved, setApproved] = useState<ApprovedRubric | null>(null);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  const refresh = () => listRubrics().then(setRubrics).catch(() => setMessage('Could not load rubrics.'));
  useEffect(() => {
    void refresh();
  }, []);

  const updateQuestion = (index: number, next: Question) =>
    setDraft((current) => ({
      ...current,
      questions: current.questions.map((question, position) => (position === index ? next : question)),
    }));

  const load = async (id: string, version: number) => {
    setBusy(true);
    setMessage('');
    try {
      const rubric = await getRubric(id, version);
      setApproved(rubric);
      setDraft({
        role: rubric.role,
        questions: rubric.questions,
        creation_source: 'revision',
        base_version: { id: rubric.id, version: rubric.version },
      });
      setMessage(`Version ${version} loaded as a revision draft.`);
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
      setDraft({
        role: result.role,
        questions: result.questions,
        creation_source: 'revision',
        base_version: { id: result.id, version: result.version },
      });
      setMessage(`Approved ${result.role}, version ${result.version}.`);
      await refresh();
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : 'Could not approve the rubric.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <main>
      <header className="hero">
        <p className="eyebrow">Recruiter pilot</p>
        <h1>Make the rubric explicit before reviewing candidates.</h1>
        <p>Every evaluation uses an approved, immutable rubric version.</p>
      </header>

      <nav aria-label="Workflow" className="steps">
        <span aria-current="step"><b>1</b> Rubric</span>
        <span><b>2</b> Resume review</span>
        <span><b>3</b> Compare</span>
      </nav>

      <div className="layout">
        <aside aria-label="Approved rubrics">
          <div className="section-heading">
            <div><p className="eyebrow">Library</p><h2>Approved rubrics</h2></div>
            <button className="secondary" onClick={() => { setDraft(blankDraft()); setApproved(null); setMessage(''); }}>
              New
            </button>
          </div>
          {rubrics.length === 0 ? <p className="muted">No approved rubrics yet.</p> : rubrics.map((rubric) => (
            <section className="rubric-summary" key={rubric.id}>
              <h3>{rubric.role}</h3>
              <div className="version-list">
                {rubric.versions.map((version) => (
                  <button className="version" disabled={busy} key={version.version} onClick={() => load(rubric.id, version.version)}>
                    v{version.version} <small>{new Date(version.created_at).toLocaleDateString()}</small>
                  </button>
                ))}
              </div>
            </section>
          ))}
        </aside>

        <section className="workspace" aria-labelledby="editor-title">
          <div className="section-heading">
            <div>
              <p className="eyebrow">{draft.base_version ? `Revision of v${draft.base_version.version}` : 'Manual draft'}</p>
              <h2 id="editor-title">Rubric editor</h2>
            </div>
            {approved && <span className="badge">Latest approval: v{approved.version}</span>}
          </div>

          <label>
            Role
            <input value={draft.role} onChange={(event) => setDraft({ ...draft, role: event.target.value })} placeholder="e.g. Backend engineer" />
          </label>

          <div className="questions">
            {draft.questions.map((question, index) => (
              <QuestionEditor
                index={index}
                key={question.id}
                question={question}
                update={(next) => updateQuestion(index, next)}
                remove={() => setDraft({ ...draft, questions: draft.questions.filter((_, position) => position !== index) })}
              />
            ))}
          </div>

          <div className="add-row" aria-label="Add a question">
            <span>Add question</span>
            {(['choice', 'score', 'noul'] as const).map((type) => (
              <button className="secondary" key={type} onClick={() => setDraft({ ...draft, questions: [...draft.questions, newQuestion(type)] })}>
                {type === 'noul' ? 'Yes / no' : type[0].toUpperCase() + type.slice(1)}
              </button>
            ))}
          </div>

          {message && <p className="notice" role="status">{message}</p>}
          <div className="actions">
            <p className="muted">Approval creates a permanent version. Later edits become a new version.</p>
            <button disabled={busy || !draft.role.trim() || draft.questions.length === 0} onClick={approve}>
              {busy ? 'Working…' : draft.base_version ? 'Approve new version' : 'Approve rubric'}
            </button>
          </div>
        </section>
      </div>
    </main>
  );
}

function QuestionEditor({ index, question, update, remove }: { index: number; question: Question; update: (question: Question) => void; remove: () => void }) {
  const changeType = (type: Question['type']) => update({ ...newQuestion(type), id: question.id, domain: question.domain, instructions: question.instructions });
  return (
    <fieldset className="question-card">
      <legend>Question {index + 1}</legend>
      <div className="question-grid">
        <label>Domain<input value={question.domain} onChange={(event) => update({ ...question, domain: event.target.value })} /></label>
        <label>Answer type<select value={question.type} onChange={(event) => changeType(event.target.value as Question['type'])}><option value="choice">Choice</option><option value="score">Score</option><option value="noul">Yes / no</option></select></label>
      </div>
      <label>Instructions<textarea rows={2} value={question.instructions} onChange={(event) => update({ ...question, instructions: event.target.value })} placeholder="Ask about evidence documented in the resume." /></label>
      <CriteriaEditor question={question} update={update} />
      <div className="question-footer"><code>{question.id}</code><button className="danger" onClick={remove}>Remove</button></div>
    </fieldset>
  );
}

function CriteriaEditor({ question, update }: { question: Question; update: (question: Question) => void }) {
  if (question.type === 'score') {
    const levels = question.criteria as string[];
    return <div className="criteria"><span>Ordered levels</span>{levels.map((level, index) => <div className="criterion" key={index}><b>{index}</b><input value={level} onChange={(event) => update({ ...question, criteria: levels.map((item, position) => position === index ? event.target.value : item) })} /><button className="icon" aria-label={`Remove level ${index + 1}`} disabled={levels.length <= 2} onClick={() => update({ ...question, criteria: levels.filter((_, position) => position !== index) })}>×</button></div>)}<button className="secondary" disabled={levels.length >= 10} onClick={() => update({ ...question, criteria: [...levels, ''] })}>Add level</button></div>;
  }
  const criteria = question.criteria as Record<string, string>;
  const entries = Object.entries(criteria);
  const fixed = question.type === 'noul';
  return <div className="criteria"><span>{fixed ? 'Yes / no meaning' : 'Choices'}</span>{entries.map(([label, description], index) => <div className="criterion" key={`${label}-${index}`}><input aria-label="Label" disabled={fixed} value={label} onChange={(event) => update({ ...question, criteria: Object.fromEntries(entries.map((entry, position) => position === index ? [event.target.value, entry[1]] : entry)) })} /><input aria-label={`${label} description`} value={description} onChange={(event) => update({ ...question, criteria: Object.fromEntries(entries.map((entry, position) => position === index ? [entry[0], event.target.value] : entry)) })} />{!fixed && <button className="icon" aria-label={`Remove ${label}`} disabled={entries.length <= 2} onClick={() => update({ ...question, criteria: Object.fromEntries(entries.filter((_, position) => position !== index)) })}>×</button>}</div>)}{!fixed && <button className="secondary" disabled={entries.length >= 255} onClick={() => update({ ...question, criteria: { ...criteria, [`option_${entries.length + 1}`]: '' } })}>Add choice</button>}</div>;
}
