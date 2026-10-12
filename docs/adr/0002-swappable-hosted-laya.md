# ADR 0002: Swappable Laya backend, hosted pilot first

Date: 2026-10-12
Status: Accepted; Boundless selected for the pilot. Live contract and real-resume privacy qualification remain outstanding.
Supersedes: ADR 0001's default of in-process CPU Laya; the remaining stack decisions stand.

## Context and decision

Rubric should support third-party hosted Laya, our own hosted Laya, and optional in-process inference through the same evaluation interface. For this pilot, select Boundless to avoid a dedicated-compute bill and operating a model server before usage justifies them. Privacy remains a product requirement; provider selection does not establish acceptable real-resume data handling.

Keep one `evaluate(state, questions)` interface. The Laya module owns endpoint serialization, authentication, timeouts, context checks, answer validation, and backend identity. Inject the selected adapter once when composing the backend. The editor, rubric schema, comparison orchestrator, and result display do not change when the endpoint changes. Implement one HTTP adapter first; a compatible self-hosted `laya-serve` is another URL for that adapter. A genuinely different provider protocol gets an adapter at the same seam. Optional local execution is a later adapter; do not build a plugin registry or implement every transport now.

Select `LAYA_BACKEND=http`, `LAYA_URL=https://api.inference.boundless.network/v1/systemone`, `LAYA_MODEL=convaiinnovations/laya`, and `LAYA_MAX_LEN=8192`. `LAYA_API_KEY` stays blank in the example; a Boundless bearer key belongs only in the server environment when the application is wired. Boundless documents automatic checkpoint routing, so selection adopts that transport/model identifier without claiming explicit multilingual control or verified full-context behavior. Local checkpoint/device/cache settings apply only to a future `local` backend. No hidden downloads, automatic switch to another host, or fallback to shorter-context models is allowed.

## Hosting cost tradeoff

Illustrative public compute prices checked on this date, in USD: DigitalOcean shared CPU VMs cost $48/month for 4 vCPU/8 GB and $96/month for 8 vCPU/16 GB. Hugging Face's dedicated T4 is $0.50/hour, or $365 at 730 hours/month. These are comparison points, not measured Laya capacity or the cheapest possible hosting offers. Taxes, optional services, and operating time are extra. See [DigitalOcean pricing](https://www.digitalocean.com/pricing/droplets) and [Hugging Face pricing](https://huggingface.co/docs/inference-endpoints/main/support/pricing).

Pay-per-token hosted inference avoids that idle-compute bill. Revisit our own hosting when measured usage makes it economical, latency demands it, or a customer needs tighter data control. Local/on-premises execution remains a deployment option for customers who cannot send resumes to an inference provider.

## Hosted shortlist

These are provider-published claims checked on 2026-10-12, not tested service guarantees. Both are independent of the Laya model authors.

| Candidate | Published price and interface | Open questions / pilot suitability |
| --- | --- | --- |
| Boundless (selected) | Currently free Laya calls; `https://api.inference.boundless.network/v1/systemone`, model `convaiinnovations/laya`. Documents `max_len` up to 8192, 48-token criteria limit, 422 instead of truncation, and input usage counted per question. | Selected for the pilot; begin with synthetic contract tests. Documentation describes automatic English/multilingual routing, so equivalent full-context behavior still needs confirmation. Free pricing is not a permanent commitment. |
| laya-ai.com | $0.05 per million input tokens, output free, 20 trial calls; `https://api.laya-ai.com/v1/systemone`. Advertises explicit `model=multilingual`, `max_len`, and `head_max_len`. | Alternative paid candidate for the required checkpoint controls. API page retrieval was unreliable; indexed provider documentation supplies these claims. Retention, processing region, contractual terms, billing token accounting, and rejection instead of truncation still need verification. |

Sources: [Boundless System One](https://inference.boundless.network/docs/system-one), [Boundless model listing](https://inference.boundless.network/models/convaiinnovations/laya), and [laya-ai.com API/pricing](https://laya-ai.com/laya-api). The latter describes a service verified against Laya 0.3.22, so it must not be assumed to match the installed optional local package 0.4.4.

Illustrative paid cost: if one comparison bills 60,000 input tokens (roughly a 3,000-token resume counted for each of 20 questions, before additional question overhead), $0.05/million means $0.003 per resume, $3 per 1,000, or $30 per 10,000. This is arithmetic from an assumed billed usage, not a provider quote. Providers may account for shared state differently; measure returned `usage` and actual charges with synthetic data. Drafting/Jev charges and application hosting are separate. Keep the rubric's questions in one request and avoid automatic billable retries in the pilot.

## Privacy and qualification

Rubric's no-persistence rule covers our application, not a remote provider. Hosted Laya receives reviewed resume text just as Jev does; do not claim resumes remain local or promise that leaks are impossible. Tell the recruiter the configured recipients before evaluation. Keys and endpoint choice are backend deployment settings, not arbitrary URLs supplied through the recruiter UI.

Boundless's terms permit necessary retention for providing, securing, improving, or maintaining the service, acknowledge infrastructure-provider access, and offer no uptime commitment. They also restrict sensitive content and license access for internal business purposes; suitability for a recruiter product offered to customers needs confirmation. This is not verified zero retention. See [Boundless terms, sections 1-3](https://inference.boundless.network/terms). laya-ai.com's API pricing page does not establish an enforceable resume-retention policy; do not infer one from price or marketing.

TypeSafe states no training on inputs/outputs and offers enterprise zero retention requiring setup; its standard DPA does not specify a fixed API-content deletion window. See [TypeSafe enterprise](https://typesafe.ai/enterprise) and [DPA](https://typesafe.ai/legal/data-processing). The same privacy review applies to both evaluators.

Before a provider is used for real resumes, record its permitted use, input/output retention and training terms, region/subprocessors, staff access and deletion controls, and whether a suitable data-processing agreement or zero-retention arrangement is available. Until then, use synthetic resumes for endpoint testing. Qualification must also cover all three question types, checkpoint/full-context behavior, criteria/head budgets, no silent truncation, metadata, malformed answers, timeouts, rate limits, token billing, and measured latency/quality. The adapter and Boundless defaults are implemented; account setup and live requests remain operator qualification work.

## Consequences and verification

The application remains modular without operating extra infrastructure now. Core-only Python dependencies suffice for HTTP inference; existing local runtime pins/lock remain available as an optional installation. Hosted failure preserves Jev's result, and changing the configured backend cannot alter approved rubric versions or silently route the resume elsewhere.

Documentation/configuration consistency, source links, adapter interchangeability through configuration, independent failures, and synthetic response-contract tests are checked. Live endpoint behavior, cost measurements, and provider privacy qualification remain outstanding. See [architecture](../architecture.md) and [product](../product.md).
