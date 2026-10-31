# Juriscope · product definition

Juriscope answers questions on the Spanish Criminal Code (Ley Orgánica 10/1995, `BOE-A-1995-25444`). Every statement cites the
article it rests on, every cited article is shown in full in the version that applies, and Juriscope refuses when the Code does not
support an answer. The lawyer reviews and decides.

This document is the product contract: the client, the process it changes, the requirements with their acceptance criteria, the
KPIs that prove the value, and the service levels. Architecture, operations, threats and responsible AI live in their own documents
under `docs/`.

## 1. Client and problem

**The client** is a fictional mid-size criminal-law firm in Madrid: 14 lawyers, 4 paralegals and a knowledge lead. Every figure in
this section is the firm's own estimate, given in discovery on 2026-10-30; Juriscope measures the real values through its KPIs.

**The pain.** The firm handles about **350 research questions a month**. Each takes 50 to 115 minutes, with a median of about 80,
which comes to about **470 lawyer-hours a month** (350 × 80 min). The expensive risk is not the time: it is citing a wording of the
Criminal Code that was not in force on the date of the facts. The Code has been amended many times since 1995, and the version that
applies to a case is the one in force when the facts happened, not the one on the screen today.

**What the firm buys.** Research support that removes the search, reading and version-checking steps without removing the lawyer's
judgement:

- every claim cited to an article of the Code, with a link to the official text;
- the whole article, verbatim, never a fragment;
- the version in force today or on the date of the facts, with the amending law;
- an explicit refusal when the Code does not support an answer;
- a safe way to change prompts and models: nothing reaches the lawyers without passing an evaluation gate.

**Source data.** The consolidated text of the Code and its version history, published by the Agencia Estatal Boletín Oficial del
Estado through its open-data API and the consolidated PDF. The consolidated text is informative only; it is reused under the
conditions of Ley 37/2007: the source and last-update date are shown, no endorsement is implied, and any modification is marked.

## 2. Process

### As-is

A lawyer receives a question and delimits the legal issue (5–10 min). They identify the possible offences and the articles involved
(5–15 min), find those provisions in the BOE or a legal database (5–10 min) and read the full articles with all their sections
(5–15 min). They then check every amendment to know which wording was in force on the date of the facts (5–15 min), read related
articles and contrast their reading (10–20 min), draft a note with references (10–20 min) and review the grounds and how they apply to
the case (5–10 min). A question of moderate complexity takes **50–115 minutes**, and the version check depends entirely on the
lawyer's diligence.

### To-be

The lawyer still delimits the question (5–10 min) and asks it in Juriscope. In under 8 seconds Juriscope does the machine part of
steps 2 to 6: the *Analyst* agent extracts the legal concepts, Spanish search queries and the date of the facts; hybrid and semantic
search finds the candidate provisions; the whole articles are rebuilt from the official version store; the version in force today,
or on the date of the facts, is selected with its amending law; the *Counsel* agent drafts claims that cite only the retrieved
articles; and code verification drops any claim whose citations were not retrieved. The lawyer reads the cited answer, the full
articles and the "See also" references (5–10 min), drafts the note (10–20 min) and reviews it (5–10 min). The total is
**25–50 minutes**.

That saves 25 to 65 minutes per question, which is about **146 to 379 lawyer-hours a month** at 350 questions. These are estimates
from the firm's figures; K1 measures the real time to an accepted answer.

### Steps, roles and times

| Step | As-is: who and what | Time | To-be: who and what | Time |
|---|---|---|---|---|
| 1 Reception | Lawyer delimits the legal question | 5–10 min | Lawyer, the same | 5–10 min |
| 2 Identification | Lawyer lists possible offences and articles | 5–15 min | Juriscope: *Analyst* extracts concepts, search queries and the date of the facts | ≤ 8 s for steps 2–6 |
| 3 Search | Lawyer finds the provisions in the BOE or a database | 5–10 min | Juriscope: hybrid and semantic search over the Code | |
| 4 Reading | Lawyer reads the full articles | 5–15 min | Juriscope: whole articles rebuilt from the official version store | |
| 5 Verification | Lawyer checks amendments and the version in force | 5–15 min | Juriscope: version in force today or on the date of the facts, with the amending law | |
| 6 Contrast | Lawyer reads related articles | 10–20 min | Juriscope: cited claims and "See also" articles; the lawyer reads the answer and the articles | 5–10 min |
| 7 Drafting | Lawyer drafts a note with references | 10–20 min | Lawyer, the same (out of scope) | 10–20 min |
| 8 Review | Lawyer checks the grounds and their application | 5–10 min | Lawyer, the same | 5–10 min |
| **Total** | | **50–115 min** | | **25–50 min** |

The two process maps (BPMN 2.0, Descriptive conformance sub-class) are drawn from this table for the README and the demo.

## 3. Users and roles

| Role | Uses Juriscope to | Access |
|---|---|---|
| Lawyer | ask, read cited articles, copy answers, rate them | app role `Juriscope.User` |
| Paralegal | prepare research for lawyers | app role `Juriscope.User` |
| Knowledge lead | read the KPI workbook and the feedback | Reader on the production resource group, granted outside the product |

One firm and one Microsoft Entra ID tenant. Every user sees only their own conversations. There are 18 seats (14 lawyers and 4
paralegals).

## 4. Requirements

Priorities follow MoSCoW. Every *Must* is proven by a test, live evidence and a demo take.

| ID | Priority | Story |
|---|---|---|
| REQ-01 | Must | As a lawyer I want every legal statement to cite the article it rests on, with a link to the official text |
| REQ-02 | Must | As a lawyer I want the whole cited article, not a fragment |
| REQ-03 | Must | As a lawyer I want the version that applies |
| REQ-04 | Must | As a lawyer I want an explicit refusal when the Code does not support an answer |
| REQ-05 | Must | As the knowledge lead I want every change to prompts, agents or models to pass an evaluation gate |
| REQ-06 | Must | As a lawyer I want my conversations saved, so I can list, resume and delete them |
| REQ-07 | Must | As the firm I want only signed-in members with the role to use it, each seeing only their own conversations |
| REQ-08 | Should | As a lawyer I want the articles the cited article refers to |
| REQ-09 | Should | As the knowledge lead I want 👍/👎 on each answer |
| REQ-10 | Should | As the firm I want conversations kept no longer than needed |
| REQ-11 | Could | As a lawyer I want the answer in the language of my question |
| SLA-01 | SLA | Availability of at least 99.5 % a month |
| SLA-02 | SLA | 95 % of standard questions answered in under 8 seconds |

### Acceptance criteria

**REQ-01 · Cited claims (Must)**
- **Given** an in-scope question about the Criminal Code,
- **when** Juriscope answers,
- **then** every claim carries at least one numbered citation, every citation is an article retrieved for this question, and every
  link opens `https://www.boe.es/buscar/act.php?id=BOE-A-1995-25444#<block id>`.

**REQ-02 · Full article (Must)**
- **Given** an answer with citations,
- **when** the lawyer opens a citation,
- **then** they see the full article text, verbatim in Spanish, with its number and title, rebuilt from the official BOE block.

**REQ-03 · Version that applies (Must)**
- **Given** a question that states no date,
- **when** Juriscope answers,
- **then** each cited article shows the version in force today, with its in-force date and the amending law.
- **Given** a question that states the date of the facts,
- **when** Juriscope answers,
- **then** it quotes the version in force on that date and, if it differs from the current one, shows the current version beside it.

**REQ-04 · Refusal without grounds (Must)**
- **Given** a question about case law, another law, or facts the Code does not cover,
- **when** Juriscope cannot ground a claim in a retrieved article,
- **then** it refuses with the reason (`out_of_scope`, `no_evidence` or `content_filter`) and a suggestion, and does not answer from
  model knowledge.

**REQ-05 · Evaluation gate (Must)**
- **Given** a pull request that touches the prompts, the agents, the workflow, retrieval or the evaluation,
- **when** `eval.yml` runs,
- **then** the pull request shows each evaluator's score in a comment, and it is blocked if any threshold in `eval/thresholds.yaml`
  fails.

**REQ-06 · Saved conversations (Must)**
- **Given** a previous conversation,
- **when** the lawyer opens it from the sidebar,
- **then** they see its turns with their citations, and a follow-up question uses its context.
- **Given** a conversation,
- **when** the lawyer deletes it, or deletes all of theirs, after confirming,
- **then** its history and its record are gone.

**REQ-07 · Signed-in members only (Must)**
- **Given** a request without a session, **then** the API answers 401.
- **Given** a session without the `Juriscope.User` role, **then** the API answers 403.
- **Given** a signed-in user and another user's conversation id, **then** the API answers 404.

**REQ-08 · See also (Should)**
- **Given** a cited article that refers to other articles,
- **when** the answer is shown,
- **then** those articles appear under "See also", with links to the official text.

**REQ-09 · Feedback (Should)**
- **Given** an answer,
- **when** a user rates it 👍 or 👎,
- **then** a `FeedbackGiven` event reaches Application Insights, without the question or the answer text.

**REQ-10 · Retention (Should)**
- **Given** a conversation idle for 90 days,
- **when** its time to live expires,
- **then** Cosmos DB deletes its history and its record through the container TTL (7,776,000 seconds).

**REQ-11 · Language of the question (Could)**
- **Given** a question in English,
- **when** Juriscope answers,
- **then** the answer is in English and the quoted article text stays in Spanish.

**SLA-01 · Availability**
- **Given** a calendar month in production,
- **when** successful `/api` requests are divided by all `/api` requests, counting every 5xx as a failure,
- **then** the ratio is at least 99.5 %.

**SLA-02 · Response time**
- **Given** standard questions in production (one in-scope question of moderate complexity, like the golden evaluation set),
- **when** the time is measured from the request to the final server-sent event,
- **then** 95 % of them finish in under 8 seconds.

### Won't, in this release

Case law; other laws (Ley de Enjuiciamiento Criminal and the rest); drafting or exporting documents; uploading documents; several
firms; mobile apps; Spain's co-official languages. Also rejected, each in ADR-011: multi-region, Front Door, API Management, feature
flags, Managed Grafana, Azure Load Testing, development environments in Azure, separate subscriptions and certifications.

## 5. KPIs

Each KPI is computed from custom events in the Application Insights `customEvents` table and shown in the KPI workbook, declared in
Bicep, with its target and a cross when it is missed. Events never carry the question or answer text. `user_hash` is the first 16
hexadecimal characters of the SHA-256 of the user's Entra object id.

| KPI | Definition and formula | Events | Target | Today |
|---|---|---|---|---|
| K1 Time to accepted answer | median of the minutes from `QuestionAsked` to the first `AnswerAccepted` (copy or 👍) of the same turn | `QuestionAsked`, `AnswerAccepted` | ≤ 10 min | 30–75 min for steps 2–6 |
| K2 Grounded first draft | answered turns whose draft needed no claim removal ÷ answered turns | `AnswerDelivered` (`outcome`, `claims`, `dropped_claims`) | ≥ 95 % | not measured |
| K3 Helpful answers | 👍 ÷ (👍 + 👎) | `FeedbackGiven` | ≥ 80 % | not measured |
| K4 Weekly active seats | distinct `user_hash` with `QuestionAsked` in an ISO week ÷ 18 seats (a workbook parameter) | `QuestionAsked` | ≥ 70 % | 0 |

### Events

| Event | Sent when | Properties, at least |
|---|---|---|
| `QuestionAsked` | the ask route accepts a question | `turn_id`, `user_hash` |
| `AnswerDelivered` | the turn ends with an answer or a refusal | `turn_id`, `outcome` (`answer` or the refusal reason), `claims`, `dropped_claims`, `cost_eur` |
| `AnswerAccepted` | the user copies an answer or rates it 👍 | `turn_id`, `via` (`copy` or `up`) |
| `FeedbackGiven` | the user rates an answer | `turn_id`, `value` (`up` or `down`) |

- **K1** pairs `QuestionAsked` and the first `AnswerAccepted` by `turn_id`; turns never accepted are counted apart and shown beside it.
- **K2** counts only `AnswerDelivered` with `outcome == "answer"`; a turn is grounded at first draft when `dropped_claims == 0`.
- Every KPI figure is published with its date, window and number of cases.

## 6. Non-functional requirements and SLOs

The SLOs are internal targets, stricter than the SLAs, so that an SLO miss warns before an SLA breach.

| Item | Value | Measured by |
|---|---|---|
| Availability SLO | ≥ 99.7 % | `requests` on `/api/*`, over 30 days, both in business hours and around the clock |
| Latency SLO | p95 < 6 s | `requests` duration of the ask route, to the final event |
| Error SLO | < 1 % 5xx | `requests` |
| Cost per question | ≤ 0.05 € all-in, in production | `AnswerDelivered.cost_eur` plus the fixed monthly cost ÷ questions |
| RTO | 4 h | the restore drill on staging |
| RPO | 15 min | Cosmos DB continuous backup, 7-day tier |
| Business hours | Monday to Friday, 08:00–21:00 Europe/Madrid | |
| Health model | flows *Ask*, *History* and *Model*, each healthy, degraded or down from its SLIs | the workbook |
| Accessibility | WCAG 2.2 AA, keyboard-only use, visible focus | axe-core in CI |
| Languages | the interface in English; answers in the language of the question; article text verbatim in Spanish | the language evaluator |

**Health model.** *Ask* is the ask route's availability and p95; *History* is the conversation routes and the Cosmos DB dependency;
*Model* is the Foundry dependency, including `429` responses. A flow is **healthy** while it meets its SLO over the last hour,
**degraded** when it misses the SLO but most requests still succeed, and **down** when most requests fail.

**Availability rests on a shared search service** with one replica and no financially backed SLA. A second replica would cost about
64.88 € a month against a 25 € production budget, so availability is measured, not inherited (ADR-007).

### Data and privacy

- **Classification.** Questions may hold special-category data (GDPR article 10, criminal matters) and are covered by professional
  secrecy. The interface asks users not to paste client identities.
- **Residency.** At rest in the EU: Cosmos DB, Storage and Application Insights in Sweden Central, Azure AI Search in Spain Central.
  Inference runs on shared Global Standard deployments, which may process outside the EU; ADR-009 records this and the Data Zone EU
  alternative.
- **Retention and deletion.** 90 days through the container TTL (REQ-10); one conversation or all of a user's on request (REQ-06).
- **Backup.** Cosmos DB continuous backup, 7-day tier, rehearsed with a restore drill.
- **Telemetry.** No question or answer text; users appear only as `user_hash`.

## 7. Glossary

| Term | Meaning |
|---|---|
| Block id | The BOE identifier of a provision inside the consolidated text; it is not always `a<number>` (article 142 bis is `a1-2`) |
| Version | One wording of an article, with the law that introduced it and the date it came into force |
| Claim | One statement of an answer, with the ids of the articles it cites |
| Refusal | A deliberate outcome with a reason, not an error |
| Turn | One question and its answer or refusal, inside a conversation |
