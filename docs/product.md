# Rubric recruiter pilot

Status: design contract for the next milestone. This repository currently contains dependencies, configuration, and documentation; no recruiter workflow is implemented.

## Terms

| Term | Meaning |
| --- | --- |
| Role | The job being assessed, identified by a recruiter-readable title. |
| Domain | A role-relevant area such as backend development or communication. |
| Question | A stable ID, domain, instructions, and typed criteria used by both evaluators. |
| Draft | An editable, unapproved rubric. It cannot be used for evaluation. |
| Approved version | An immutable snapshot of a role and its questions and criteria, with creation source and a UTC timestamp. |
| Reviewed text / state | Extracted resume text after recruiter corrections; the identical input sent to both evaluators. |
| Outcome | One provider's validated domain answers or its actionable error, with elapsed time. |

## Create and approve

Assisted creation starts with a role and job description. A configured OpenAI-compatible drafting endpoint proposes questions and criteria. The recruiter edits the validated draft. Manual creation starts with an empty editor and uses the same question format and validation. An empty manual draft is editable but cannot be approved.

Both modes converge on the same editor and an explicit approval action. Approval persists an immutable version. Editing an approved version copies it into a draft; another approval creates the next version under the same rubric ID. Old versions remain retrievable. Keep question IDs when meaning is unchanged; assign a new ID to a replacement question. A selected version never silently moves to the latest version.

Creation source is `assisted` or `manual` for initial creation and `revision` with a base-version reference for edits. Approval time, ID, and version number are assigned by the backend. Invalid or incomplete assisted output is an error, not an approvable draft.

## Review one resume

The recruiter uploads one text PDF of at most 10,000,000 bytes (10 MB), reviews and corrects the extraction, and selects an approved rubric version. Evaluation is an explicit action after review. Both providers receive the same reviewed text and questions. Editing text or changing the selected version clears displayed results; a late response from an older evaluation must not overwrite newer state.

Display results grouped by domain and question, separately for Jev and the configured Laya backend: typed answers, distributions when provided, provider-specific confidence when provided, elapsed time, and errors. Preserve a successful result if the other provider fails. A retry evaluates the same snapshot; changing inputs starts a new comparison. No overall score, candidate ranking, or automated hiring decision is part of the pilot.

## Evidence semantics and privacy

Answers describe evidence present in the reviewed resume, not verified ability or facts about a candidate. Missing evidence is not proof that a skill is absent. Criteria should explicitly describe insufficient evidence, and propositions should ask whether the resume documents a fact rather than assume it is true. A `noul` value is the provider's yes probability; it is not a separate correctness-confidence field. Confidence and distributions are provider-specific signals, not a common accuracy score. Model agreement does not verify evidence. Recruiters retain responsibility for interpretation.

The pilot displays reviewed source text alongside answers. The typed evaluators do not promise supporting quotations; do not invent evidence excerpts or explanations from their numeric outputs. Quality and calibration on resumes require later measurement.

Resume files, reviewed text, and results live only in active application memory and are cleared when replacing the resume, resetting, or ending the session. Do not write them to logs, browser storage, SQLite, exports, or application temporary files. Operating-system paging and provider-side retention are outside that application-level policy. Jev and the selected third-party Laya endpoint receive reviewed candidate text remotely; the drafting provider receives only the job description. A future self-hosted HTTP or local Laya adapter changes the Laya recipient without changing the rubric workflow. Hosted inference is the pilot default; local-only processing is not a claim this pilot can make. The pilot must make those destinations clear before use, and provider retention must be checked before real candidate data is used. Job descriptions and rubric criteria must not embed candidate data.

## Acceptance criteria for the application milestone

1. Manual and assisted creation converge on the same editable draft and explicit approval. Missing drafting settings give a clear error while manual editing remains available.
2. Draft validation rejects empty roles, empty question sets, duplicate IDs, unknown types, missing instructions, and invalid criteria. Model output never bypasses validation or approval.
3. Approval assigns an immutable version and timestamp; revising it creates another version without overwriting earlier content. Evaluation rejects nonexistent or unapproved references.
4. Oversized, malformed, encrypted/unreadable, scanned, or empty PDFs give actionable extraction errors. Corrected, nonempty text is reviewed before evaluation.
5. Both adapters evaluate an identical snapshot. The UI shows domain answers and provider errors independently, with distributions, available confidence, and timing. Stale results cannot attach to changed inputs.
6. Invalid provider IDs, labels, types, or numeric values are errors. Inputs beyond a provider's token budget fail explicitly rather than being truncated. Switching a qualified Laya endpoint leaves the editor, question schema, and comparison workflow unchanged; results identify the backend and served model. Missing settings fail clearly without hidden local downloads or requests to another host.
7. Replacing/resetting a resume clears candidate state. Application logs, database, browser persistence, temporary files, and repository artifacts contain no candidate data.

## Pilot boundaries

One recruiter on localhost, one resume at a time, text PDFs only, editable extraction, and domain results only. OCR, batch processing, ranking, public deployment, authentication, model downloads, and performance/quality benchmarking are deferred. This pilot selects Boundless for hosted Laya; own-server and local inference remain design options for later adapters. The selected endpoint still requires qualification of retention suitability, full-context behavior, latency, cost per resume, and classification quality. See [hosted Laya decision](adr/0002-swappable-hosted-laya.md).
