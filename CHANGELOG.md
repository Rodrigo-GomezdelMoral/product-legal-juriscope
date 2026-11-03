# Changelog

All notable changes to Juriscope are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
  the model double, then the real model on the warm stable revision; `release.yml` promotes the staged digest to production with
  a 10 % canary, a health check and rollback (ADR-012, ADR-015).
- Operations: `docs/OPERATIONS.md` (promotion, rollback, urgent patch, alerts, restore drill, incident procedure, load tests,
  DORA), `docs/THREAT_MODEL.md`, `docs/RESPONSIBLE_AI.md`, `docs/evaluation.md`, `docs/cost.md` and ADR-001 to ADR-016.

### Verified in staging

- Every *Must* in the browser as a user, with the final state on screen; sign-in through Easy Auth and the code flow
  (2026-11-01 and 2026-11-03).
- Full evaluation suite on `jur-articles-stg` (2026-11-01, 110 cases): recall@5 0.917, citation precision 1.000, version accuracy
  1.000, correct refusal 1.000, false refusal 0.027, canary 0, groundedness 0.994.
- SLA-02 (2026-11-03, `load-test.yml`): 45 real-model answers, p95 12.0 s against 15 s, 0 failed; progress shown in 10 to 27 ms.
- Restore drill: 12 min 17 s from the decision to readable data, against a 4 h RTO.

[Unreleased]: https://github.com/Rodrigo-GomezdelMoral/product-legal-juriscope/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Rodrigo-GomezdelMoral/product-legal-juriscope/releases/tag/v1.0.0
