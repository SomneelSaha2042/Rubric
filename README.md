# Rubric

Rubric is a localhost recruiter pilot for defining an explicit hiring rubric, reviewing extracted resume text, and comparing Jev with Laya on Boundless. Rubric versions are immutable; candidate files, text, and evaluation results are kept in process/browser memory and are never written to the database.

The end-to-end pilot is implemented. It supports manual and assisted rubric drafts, explicit approval and revisions, bounded text-PDF extraction, human text review, and independent Jev/Boundless outcomes. Live provider calls still require your own server-side keys and synthetic qualification before real resumes are used.

Read the [product contract](docs/product.md), [architecture](docs/architecture.md), [stack ADR](docs/adr/0001-local-pilot-stack.md), and [hosted Laya decision](docs/adr/0002-swappable-hosted-laya.md).

## Windows setup

Use Python 3.12 x64 and Node 22. From the repository root in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
Push-Location frontend
npm ci --no-audit --no-fund
Pop-Location
```

Edit `.env` on the server machine. `LAYA_URL`, model, and 8192-token limit are already set for Boundless; add `LAYA_API_KEY`. Add `JEV_API_KEY` for Jev. Assisted drafting also needs a full Chat Completions URL, model, and key. Blank settings produce clear per-feature errors and never trigger a model download. No secret belongs in a `VITE_*` variable.

| Setting | Purpose |
| --- | --- |
| `DRAFTING_URL`, `DRAFTING_MODEL`, `DRAFTING_API_KEY` | OpenAI-compatible Chat Completions JSON-mode drafting; optional. |
| `JEV_URL`, `JEV_API_KEY`, `JEV_MODEL` | Typesafe System One endpoint and pinned `jev-1.13.0` model. |
| `LAYA_BACKEND`, `LAYA_URL`, `LAYA_API_KEY`, `LAYA_MODEL`, `LAYA_MAX_LEN` | Swappable System One HTTP backend; defaults select Boundless Laya with `max_len=8192`. |
| `SQLITE_PATH` | Approved rubric versions only; defaults to `data/rubric.sqlite3`. |

The separate `requirements-laya.txt` and platform-specific `requirements.lock.txt` preserve an optional local Laya environment. The hosted pilot does not import Laya or PyTorch and does not download weights.

## Run locally

For development, run the API and Vite in separate terminals:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

```powershell
Set-Location frontend
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` to FastAPI. For a single-process local run, build once and start FastAPI:

```powershell
Push-Location frontend
npm run build
Pop-Location
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Open `http://127.0.0.1:8000`. `/api/status` reports readiness without returning credentials.

## Verify

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m unittest discover -v
Push-Location frontend
npm ls --all
npm run build
Pop-Location
git status --short
git check-ignore .venv/ frontend/node_modules/ .env data/rubric.sqlite3 .cache/huggingface/ frontend/dist/
```

The Python suite covers schema/approval, immutable revisions, invalid assisted output, missing drafting configuration, PDF extraction failures and size limits, independent provider failure, provider-answer validation, approved-version lookup, and absence of synthetic candidate/job text from SQLite. The frontend build performs TypeScript checking and a production Vite build.

## Privacy and pilot limits

Before comparison, the UI discloses that the reviewed resume is sent to Typesafe and Boundless. Memory-only handling by this application does not control provider retention, infrastructure access, browser developer tools, or operating-system paging. Boundless and Typesafe account terms, a suitable DPA/zero-retention arrangement, region, and permitted recruiting use must be qualified before real candidate data is sent.

Use one resume at a time, text PDFs up to 10 MB and 100 pages, and domain-level evidence results. OCR, batches, overall ranking, authentication, public deployment, and automated hiring decisions remain outside this pilot. Provider latency, billing, calibration, and resume-classification quality remain unmeasured because no live credentials are stored in this repository.
