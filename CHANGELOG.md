# Changelog

All notable changes to Juriscope are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.1] - 2026-11-03

A patch from the validation of 1.0.0: the release's canary check and its rollback now do what the documents say, public run
logs stop printing identifiers, and every published figure matches its source. Only documentation, workflows and the web client
change, so no load test is required (ADR-015); the image is rebuilt from the same `app/` code.

### Fixed

- The canary check could not see the canary: it read Application Insights requests by `cloud_RoleInstance`, a per-process id,
  so it always counted 0 requests and passed. `release.yml` now reads the new revision's requests and 5xx from the Container
  Apps `Requests` metric filtered on its revision name, prints both, says when the canary got no request, and rolls back when 5xx
  exceed 1 % (ADR-012, revised).
- A rollback by `workflow_dispatch` reused the revision suffix of a revision that already exists. A dispatch now gets the suffix
  `v<major>-<minor>-<patch>-r<run number>` and takes the tag to deploy as the input `tag`, so it runs this workflow, not the old
  tag's: `gh workflow run release.yml --ref <latest tag> -f tag=<previous tag>`.
- The model retirement date: `gpt-5-mini` 2025-08-07 retires on 2027-07-13 (Models API and Learn, read 2026-11-03), not
  2027-02-09; the replacement plan moves to about March and April 2027 (ADR-010, `docs/RESPONSIBLE_AI.md`).
- The mobile drawer: Escape closes it from the menu button too and returns focus to that button, which is now labelled "Menu".
- The BOE reuse notice under each answer links to www.boe.es, as `data/README.md` states.
- The load test's replica and CPU maxima end three minutes after the real-model stage, with a fresh sign-in, instead of one
  hour after the start by Azure CLI's default.

### Security

- Public run logs printed the sign-in apps' client ids, the shared endpoints, the registry host and resource GUIDs from
  `what-if`. These values are now GitHub secrets, which logs mask, and `what-if` output replaces GUIDs. Earlier logs are kept as
  the DORA evidence.
- Dependabot ignores base-image versions beyond the pinned lines (Python 3.12, Node 24); updates within them still arrive.

### Changed

- The SLA-02 evidence is the load test on the release commit and its digest, the one in production: run 41661582947, exact p95
  12,784 ms on 96 real-model asks, 0 failed (2026-11-03). The earlier run 41619345584 on the image of `298ea6a` (p95 12.0 s on 45
  asks) stays in `docs/OPERATIONS.md` as history.
- `docs/OPERATIONS.md`: the fast rollback by revision and the planned rollback with their limits; the canary's twelve minutes;
  the RPO basis and the restore caveats; production DORA (1 release, 8 minutes from tag to production, change failure rate
  0 of 1) and staging DORA to 2026-11-03; Advisor after the release; the staging telemetry cap found at 2.0 GB; the sign-in
  secrets' expiry dates.
- `docs/RESPONSIBLE_AI.md`: status as of this release, where the app runs (France Central) and where data stays (Sweden Central),
  and the sign-off line. ADR-008 names the region and date of each cold start; ADR-014 records the rejected zone redundancy of the
  environment; the threat model states how actions are pinned and two residual risks; the README names every secret and variable.

### Known limitations (planned for the next release with a load test)

- Availability counts 5xx only, so a question that fails inside a started stream counts as available: 31 of 11,304 ask requests
  (0.27 %) in staging over 30 days, all under the stress ramps; 0 of 3 in production (2026-11-03). Planned: `success == false` in
  the tile and the alert, and a console line for the in-stream exception.
- The health model marks *Ask* degraded at a p95 of 6 s instead of the 13 s SLO, so it shows degraded almost always.
- The K1 tile shows accepted turns only, not the turns never accepted beside them.
- The canary measures requests and 5xx per revision, not its p95, until the app sets `service.instance.id` from the replica name.
- Both runtime identities read every index of the shared search service (Search Index Data Reader at service scope). Planned: the
  role on each environment's own index, through an author script.

## [1.0.0] - 2026-11-03

The first release: a criminal-law firm's lawyers ask a question about the Spanish Criminal Code and get an answer in which every
claim cites the article it rests on, every cited article is shown whole in the version in force today or on the date of the facts,
and Juriscope refuses when the Code does not support an answer. Verified in staging on 2026-11-01 to 2026-11-03; production is
created by this release after the author's approval.

### Added

- Product definition in `docs/PRODUCT.md`: the client, the process as-is and to-be, eleven requirements with acceptance criteria,
  four KPIs with their events, two SLAs with their SLOs and the health model.
- The version store: the Criminal Code's 750 articles and 23 dispositions with their 1,592 versions, from the BOE open-data API,
  with the source, the reuse conditions and every change from the source in `data/README.md`; whole articles and the version in force on any date are code,
  never the model (REQ-02, REQ-03, REQ-08).
- The graph workflow exposed as an agent, built with Microsoft Agent Framework: *Analyst* (`gpt-5-mini`) extracts the concepts,
  the Spanish queries and the date of the facts or refuses out-of-scope questions; hybrid and semantic search retrieves candidate
  articles; *Counsel* (`gpt-5-mini`) drafts claims with structured output; code drops every claim whose citations were not
  retrieved and refuses when none is left (REQ-01, REQ-04).
- A 5-second deadline and one retry on *Analyst*, because a slow model call, not the workflow, set the p95 (ADR-016).
- Conversation history in Cosmos DB through the framework's `CosmosHistoryProvider`, plus a `conversations` container for the
  sidebar; follow-ups resolve through history; list, resume and delete; a 90-day TTL (REQ-06, REQ-10).
- The evaluation gate: five datasets (golden, smoke, versions, unanswerable, adversarial), evaluators in code and the
  `azure-ai-evaluation` groundedness judge, thresholds and a baseline; `eval.yml` runs it on every pull request that changes the
  prompts, the agents, the workflow or the corpus and comments the table on the pull request (REQ-05).
- The API: server-sent events with per-step progress, then one answer or one typed refusal; problem responses with a trace id;
  401 without a session, 403 without the `Juriscope.User` role and 404 for another user's conversation; 503 with `Retry-After`
  when the model is throttled or a dependency is down (REQ-07).
- KPI events (`QuestionAsked`, `AnswerDelivered`, `AnswerAccepted`, `FeedbackGiven`) with a hashed user id and no question or
  answer text, and 👍/👎 and copy on every answer (REQ-09).
- The web client on the common chat interface: progress from the first 0.1 s, article cards with the version badge, the full
  article and both versions side by side when the date of the facts selects an older one, "See also", the BOE's reuse notice,
  answers in the language of the question (REQ-11), WCAG 2.2 AA checked with axe in CI.
- The demo mode, published on GitHub Pages: five runs recorded from staging on 2026-11-03 and an evidence panel with the gate's
  report and the recorded 401 and 404 responses.
- Infrastructure in Bicep for staging and production: one Container Apps environment in France Central shared by both apps
  (ADR-014), Cosmos DB serverless with continuous backup, Storage for the corpus, Key Vault for the sign-in secret, Application
  Insights with a daily cap, the KPI and SLO workbook, alerts, budgets and tags; the search index per environment on the shared
  search service.
- Delivery: one image per merge, deployed to staging by digest (`deploy.yml`); `load-test.yml` with Locust against a revision on
  the model double, then 10 minutes of the real model on the warm stable revision, gated on the exact p95 of every real-model ask
  rather than Locust's rounded percentile (ADR-017); `release.yml` promotes the staged digest to production with a 10 % canary, a
  health check and rollback (ADR-012, ADR-015).
- Operations: `docs/OPERATIONS.md` (promotion, rollback, urgent patch, alerts, restore drill, incident procedure, load tests,
  DORA), `docs/THREAT_MODEL.md`, `docs/RESPONSIBLE_AI.md`, `docs/evaluation.md`, `docs/cost.md` and ADR-001 to ADR-017.

### Verified in staging

- Every *Must* in the browser as a user, with the final state on screen; sign-in through Easy Auth and the code flow
  (2026-11-01 and 2026-11-03).
- Full evaluation suite on `jur-articles-stg` (2026-11-01, 110 cases): recall@5 0.917, citation precision 1.000, version accuracy
  1.000, correct refusal 1.000, false refusal 0.027, canary 0, groundedness 0.994.
- SLA-02 (2026-11-03, `load-test.yml`): 45 real-model answers, p95 12.0 s against 15 s, 0 failed; progress shown in 10 to 27 ms.
  The released commit carries its own `load-test` status, the exact p95 of about 90 real-model asks, which `release.yml` checks.
- Restore drill: 12 min 17 s from the decision to readable data, against a 4 h RTO.

[Unreleased]: https://github.com/Rodrigo-GomezdelMoral/product-legal-juriscope/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/Rodrigo-GomezdelMoral/product-legal-juriscope/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/Rodrigo-GomezdelMoral/product-legal-juriscope/releases/tag/v1.0.0
