# Rubric

Local recruiter pilot comparing Jev and a configurable Laya backend against explicitly approved, versioned rubrics. Boundless is selected for the hosted Laya pilot; self-hosted HTTP and optional local inference use the same evaluation interface.

**Current milestone: dependencies, configuration, and design documentation only.** The project-local Python environment and frontend dependencies are installed. No API, UI, model weights, database, or recruiter workflow exists yet. Development/build scripts are prepared for the later application milestone; there is no application entry point to serve or build now.

Read the [product contract](docs/product.md), [architecture and intended interfaces](docs/architecture.md), [stack ADR](docs/adr/0001-local-pilot-stack.md), and [hosted Laya decision and pricing shortlist](docs/adr/0002-swappable-hosted-laya.md).

## Windows setup

Use PowerShell, Python 3.12 x64, and Node 22 (at least 22.12). These commands do not require activating the environment or changing PowerShell's execution policy. Start at the repository root:

```powershell
Set-Location C:\Users\somne\Documents\Rubric
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Push-Location frontend
npm ci --no-audit --no-fund
Pop-Location
```

The hosted pilot needs only `requirements.txt`; HTTPX handles remote inference without PyTorch or model downloads. The existing Python lock records the optional combined core and local Laya environment resolved on Windows x64/Python 3.12. To reproduce that optional environment, install `-r requirements.lock.txt` instead; the current workspace already has it installed. To resolve combined direct pins after an intentional update, install `-r requirements.txt -r requirements-laya.txt`, run checks, then regenerate the lock. Do not copy this Windows lock to another platform without resolving and verifying its dependencies there. npm's lock records the exact frontend dependency graph.

If `.env` does not already exist, copy `.env.example` to `.env` and fill the server-side settings when the application is implemented. Leave credentials out of source control. Setup and verification require no credentials and make no inference/drafting calls.

| Setting | Intended behavior |
| --- | --- |
| `DRAFTING_URL`, `DRAFTING_MODEL`, `DRAFTING_API_KEY` | Blank by default. Full Chat Completions endpoint URL, explicitly selected model, and bearer key required for assisted drafting. Missing values must produce an actionable error; manual mode remains available. |
| `JEV_API_KEY`, `JEV_MODEL` | Server-only key; pinned model `jev-1.13.0`. Missing key becomes an independent Jev outcome error. |
| `LAYA_BACKEND` | `http` for this pilot; a later `local` adapter can use the same evaluation interface. |
| `LAYA_URL`, `LAYA_API_KEY` | Boundless System One URL is supplied; key remains blank. Put a Boundless API key in server-side `LAYA_API_KEY` when wiring the app. Missing settings produce a Laya outcome error. |
| `LAYA_MODEL`, `LAYA_MAX_LEN` | `convaiinnovations/laya`, `8192`; Boundless routes checkpoints automatically. Full-context behavior still needs synthetic validation. |
| `LAYA_CHECKPOINT`, `LAYA_DEVICE`, `HF_HOME` | Optional local adapter only: explicit multilingual checkpoint, `cpu`, ignored `.cache/huggingface`. Hosted mode ignores them and never loads weights. |
| `SQLITE_PATH` | `data/rubric.sqlite3`, approved rubric versions only. Relative paths resolve from the repository root. |

The configuration is a contract for future backend settings; no application reads `.env` yet. Never put server secrets in `VITE_*` variables. The future Vite dev server uses `127.0.0.1:5173` and proxies `/api` to `127.0.0.1:8000`; the future FastAPI process must bind to `127.0.0.1` with one worker. FastAPI will serve the built frontend in a later packaged local run.

## Verify dependencies without weights

From the root:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip check
@'
import importlib, os, sqlite3
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HF_HOME'] = '.cache/huggingface'
for name in ('fastapi', 'uvicorn', 'httpx', 'pydantic', 'pypdf',
             'python_multipart', 'dotenv'):
    importlib.import_module(name)
    print('import OK:', name)
from dotenv import dotenv_values
settings = dotenv_values('.env.example')
assert settings['LAYA_BACKEND'] == 'http'
assert settings['LAYA_URL'] == 'https://api.inference.boundless.network/v1/systemone'
assert settings['LAYA_API_KEY'] == ''
assert settings['LAYA_MODEL'] == 'convaiinnovations/laya'
assert settings['LAYA_MAX_LEN'] == '8192'
assert settings['LAYA_CHECKPOINT'] == 'convaiinnovations/laya-multilingual'
assert settings['JEV_MODEL'] == 'jev-1.13.0'
print('SQLite:', sqlite3.sqlite_version)
# No provider calls or local model construction in dependency verification.
'@ | .\.venv\Scripts\python.exe -

Push-Location frontend
node --version
npm --version
npm ls --all
npx tsc --version
npx vite --version
npx tsc --noEmit
@'
import assert from 'node:assert/strict';
import { resolveConfig } from 'vite';
const config = await resolveConfig({}, 'serve');
assert.equal(config.server.host, '127.0.0.1');
assert.equal(config.server.port, 5173);
assert.equal(config.server.strictPort, true);
assert.equal(config.server.proxy['/api'], 'http://127.0.0.1:8000');
assert.equal(config.preview.host, '127.0.0.1');
console.log('Vite configuration OK');
'@ | node --input-type=module -
Pop-Location
git status --short
git check-ignore .venv/ frontend/node_modules/ .env data/rubric.sqlite3 .cache/huggingface/ frontend/dist/
```

`npm ls --all` may list unmet optional dependencies for other platforms or features such as React Compiler and CSS preprocessors. Those features are unused; installed platform bindings and required dependencies must be valid. `tsc --noEmit` currently checks only the configuration, not an application.

Optional local-runtime check after installing the combined lock (imports only; no model construction):

```powershell
@'
import os
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HF_HOME'] = '.cache/huggingface'
from laya import Agent, Router
import torch, transformers
assert torch.ones(1, device='cpu').device.type == 'cpu'
print(torch.__version__)
'@ | .\.venv\Scripts\python.exe -
```

## Verification recorded on 2026-10-12

- All requested direct Python and frontend pins installed successfully under Python 3.12.4. Python dependencies passed `pip check`; the combined resolved environment is in `requirements.lock.txt`.
- Core, PyTorch, Transformers, Laya, and Laya's Agent/Router entry points imported successfully with Hugging Face offline mode; no model was constructed or weights loaded. PyTorch reports `2.14.1+cpu` and no CUDA build; a CPU tensor assertion passed. SQLite reports 3.45.3.
- Node v22.16.0 and npm 10.9.2; TypeScript 7.0.2 and Vite 8.3.4. npm's installed tree has no required dependency errors. TypeScript configuration and Vite loading/proxy/loopback assertions passed.
- The default configuration now selects Boundless HTTP Laya with its URL/model supplied and key blank; local runtime remains optional. Provider claims are documented, but live endpoints and their account-specific privacy terms are untested.
- Documentation links, manifest/lock/configuration consistency, and Git ignore rules were checked. No secrets, dependencies, runtime databases, candidate data, or model caches are tracked. The laya-ai.com source returned 403/timeouts during direct retrieval; its indexed pricing/contract remains a provisional source.

## What comes next

Implement and test the schemas/approval store, both creation modes, bounded in-memory PDF extraction and review, and the evaluator modules, starting with HTTP adapters. Qualify the selected Boundless endpoint against [ADR 0002](docs/adr/0002-swappable-hosted-laya.md) before real candidate use. [Architecture](docs/architecture.md#required-future-verification) defines the required validation, immutable-version, PDF-error, provider-failure, truncation-prevention, and candidate-retention tests.

This milestone intentionally defers application builds and workflow tests, model downloads, and live provider requests. Laya's CPU latency, long-context memory use, and resume-classification quality on the intended Intel-graphics, 32 GB machine remain unmeasured. Package locks do not freeze downloadable weights; pin and record the checkpoint revision when model downloads are authorized. OCR, batches, overall ranking, and public deployment remain outside the pilot.
