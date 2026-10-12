# ADR 0001: Local recruiter pilot stack

Date: 2026-10-12
Status: Accepted stack; local Laya default superseded by [ADR 0002](0002-swappable-hosted-laya.md).

The decision below records the original setup. Current pilot direction uses a swappable hosted Laya backend; installed local dependencies remain optional. Runtime quality and performance await measurement.

## Context

Rubric needs editable manual and assisted question creation, explicit immutable approval, reviewed PDF extraction, and a comparison of hosted Jev with local Laya. The first pilot has one recruiter, one resume at a time, and an Intel-graphics machine with 32 GB RAM. This milestone deliberately stops before application implementation and model downloads.

## Decision

Use React/TypeScript with Vite for the interface, FastAPI/Pydantic for server contracts, asynchronous HTTPX for drafting and Jev, pypdf for text PDFs, and built-in `sqlite3` for approved versions. Use one backend process and lazy CPU Laya inference in a worker thread. A shared evaluation contract has two adapters and preserves independent outcomes. Bind all local servers to loopback; use Vite's `/api` proxy during development and later serve the frontend through FastAPI.

Pin the requested direct dependencies:

| Area | Dependencies |
| --- | --- |
| Python 3.12 core | FastAPI 0.143.0; Uvicorn 0.54.0; HTTPX 0.28.1; Pydantic 2.14.1; pypdf 6.20.0; python-multipart 0.0.32; python-dotenv 1.2.4. |
| Separate local runtime requirements | Laya 0.4.4; PyTorch 2.14.1. |
| Frontend, Node 22 | React/React DOM 19.3.0; TypeScript 7.0.2; Vite 8.3.4; React plugin 6.1.2; React/React DOM types 19.3.0; Node types 22.20.5. |

`requirements.txt` and `requirements-laya.txt` express direct pins. `requirements.lock.txt` records the resolved Windows Python 3.12 environment; `frontend/package-lock.json` records the npm tree. Laya runtime requirements remain separate so future core-only installations can omit inference dependencies. CPU is an explicit runtime selection; a PyTorch wheel may support additional devices without changing that selection. The resolved lock is platform-specific and must be re-resolved and checked before using another OS/Python version.

Pin the hosted model to [Jev `jev-1.13.0`](https://docs.typesafe.ai/models), and explicitly select Laya's multilingual checkpoint and `max_len=8192` as described in [Laya's documentation](https://github.com/NandhaKishorM/laya). Package locking does not pin downloadable model weights; record and pin the checkpoint revision in the later model-download milestone. Reject over-budget inputs rather than truncate them.

Use configurable Chat Completions JSON mode plus local rubric validation for assisted drafting, retaining compatibility with supporting OpenAI-compatible endpoints. [JSON mode does not enforce schema adherence](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat). Leave endpoint, drafting model, and keys unset until explicitly configured; unsupported or missing configuration is a clear error.

## Consequences

Only approved rubric versions persist. Candidate PDFs, reviewed text, and outcomes stay in application memory and are excluded from logs, browser storage, temp files, and SQLite. This reduces application retention but does not control OS paging or hosted-provider retention. Jev receives reviewed text remotely; the drafting endpoint receives job descriptions. Local Laya avoids remote inference for that adapter. These destinations and retention limitations must be communicated before real candidate use.

CPU inference avoids relying on Intel graphics support but may be slow, particularly at long context lengths. A worker thread keeps the event loop responsive; it does not make inference faster or cancellable. One model/process and a busy guard keep the single-resume pilot predictable. There is no claim yet about resume accuracy, confidence calibration, or cold/warm latency.

Defer an ORM, external database, queue, Redis, microservices, extra UI libraries, OCR, batch evaluation, aggregate ranking, and public deployment. Built-in SQLite and one process satisfy the present persistence and concurrency needs. Revisit this decision only when measured load, multiple users, image PDFs, or deployment requirements require those capabilities. Authentication and production hosting need a separate design before leaving localhost.

## Verification

Dependency installation, dependency-tree consistency, imports without weights, tool versions, configuration, links, and Git exclusions are checked in this milestone. See [README](../../README.md) for reproducible commands and recorded outcomes and [architecture](../architecture.md) for future behavioral tests.
