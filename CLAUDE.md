# CLAUDE.md, working agreement

`product-legal-juriscope` is **Juriscope**: cited answers on the Spanish Criminal Code, with the full article and the version in
force, for the lawyers of a mid-size criminal-law firm. A staff engineer and a head of product will read this repository for ten
minutes and must conclude that the author ships products a company would put in front of its clients: a client with requirements,
numbers that prove the value, and a safe way to change it. That conclusion depends on **restraint**: how little code produces the
result, and whether every remaining line expresses a decision someone could defend.

Three rules govern every choice:

> **If a capability exists in an Azure service or in Microsoft Agent Framework, do not reimplement it.**
>
> **If a task can be written as a function, write a function, not an agent.** Juriscope has two agents (*Analyst* and *Counsel*)
> and one graph workflow because the flow branches to a refusal at two points, streams progress per step and keeps conversation
> history natively (ADR-001). Retrieval, version selection and citation verification are code.
>
> **The model never decides what the law says.** It may only cite articles retrieved for the question; code drops any claim whose
> citations were not retrieved, and the article text always comes from the official version store, never from the model.

**Re-read this file at the start of every phase** and reason the plan before touching code: which `REQ` of `docs/PRODUCT.md` the
phase closes and how each will be demonstrated (a test and, from phase 7, a live check).

## Process

- The build prompt is `../_prompts/V5-CC-P07-product-legal-juriscope.md`, executed phase by phase with
  `../_00_MASTER_PROMPTS_PRODUCT/02_EJECUTAR_PROMPT_POR_FASES.md`. Read both in full; this file does not replace them.
- **Trunk-based.** One short branch per phase, created with `git switch -c` from `main` updated with `git pull --ff-only`:
  `feature/setup`, `domain`, `agents`, `eval`, `api`, `web`, `infra`, `staging`, `release`. No environment branches; never work on
  `main`.
- **Commits, pushes, PRs, merges and releases are the author's.** Never run `git add`, `git commit`, `git push`, `gh pr create`, a
  merge or a release, and never run anything in `../_scripts/`. No `Co-Authored-By` and no Claude Code line anywhere: the author is
  the only author.
- **Closing a phase, in this order:** ruff, mypy, pytest and the budget, plus the phase's own checks; conformance with its
  `Guidance map` rows; the block below; the publish script `../_scripts/product-legal-juriscope/publish-<branch>.sh` (template 7.3
  of `../_00_MASTER_PROMPTS_PRODUCT/_setup/CONFIGURACION_INICIAL.md`: only the phase's paths, commits in English, the PR body with the
  block); `git status --short`; then stop until the author merges and says "continue".

  ```
  ── PHASE n COMPLETE ──
  Files: <n>/90   Python: <n>/1,400   Tests: <n>/700   Bicep: <n>/490   TS: <n>/800   Comments: <n>/5
  Verified: ruff ✓  mypy ✓  pytest ✓  budget ✓  <phase checks>
  Requirements: REQ-xx <test> + <live evidence>; ...
  Guidance: <syllabus sections>; <Well-Architected codes>
  Publish: ../_scripts/product-legal-juriscope/publish-<branch without feature/>.sh
  ```

  The counts come from `make budget`.
- **Identity is the author's.** App registrations, role assignments, federated credentials, GitHub secrets and variables go in
  `../_scripts/product-legal-juriscope/<nn>-<what>.sh`; write the script and stop. Written: `01-codeql.sh` (phase 1), `03-eval-variables.sh`
  (phase 3), `04-eval-identity.sh` and `04-required-checks.sh` (phase 4), `05-codeql-web.sh` (phase 5, after its merge). Planned: `07-staging.sh` (phase 7, which must also give
  `gh-product-legal-juriscope-pull-request` Search Index Data Reader on `jur-articles-stg` when it switches `EVAL_SEARCH_INDEX`),
  `08-production.sh` (phase 8).
- **Azure only in phases 7 and 8.** Until then: local, the Cosmos DB emulator, Bicep `what-if`, and the shared model deployments and
  `jur-articles-local` index with the author's own identity. Before creating anything that bills by the hour, state its price and how
  it is switched off. Staging ends every deploying phase at zero replicas.
- **Verify, then write.** Every Agent Framework and Azure SDK name against the installed wheel (the framework renamed many members on
  its way to 1.x, and the syllabus guide has stale import paths); every Bicep API version, CLI flag and GA or preview status against
  Microsoft Learn. Never claim what was not checked: say whether a thing is implemented, tested, deployed to staging, deployed to
  production or pending.
- **English** in everything generated. The product answers in the language of the question and quotes article text verbatim in
  Spanish. The author is spoken to in Spanish.

## Non-negotiable constraints

1. **No identifiers anywhere,** fixtures, recorded runs and commit messages included: no GUID, e-mail address, `*.azurecontainerapps.io`
   host, Azure endpoint host, public IP, tenant domain or `C:\Users` path. Use placeholders. `tests/test_budget.py` scans every file
   and reports only the file and the kind of identifier, never the value.
2. **Zero secrets.** `DefaultAzureCredential` or `ManagedIdentityCredential` for every Azure call; local and shared-key auth disabled
   wherever the service allows it. The only secret in the system is the sign-in app's client secret, in each environment's Key Vault
   and in a GitHub environment secret (ADR-006).
3. **Budgets, enforced by `tests/test_budget.py`:** at most 90 files (excluding `docs/`, `data/`, `eval/datasets/`, `web/fixtures/`,
   `web/public/`, lock files and `node_modules/`); Python in `app/ ops/ eval/ load/` at most 1,400 non-blank lines; tests at most 700;
   Bicep at most 490; TypeScript under 800; functions at most 35 lines.
4. **Comments:** at most 5 in all the code (Python `#`, Bicep and TypeScript `//`, and `#` in workflows, `Makefile` and
   `Dockerfile`). The why goes in the ADRs and the README. Every block that exists only because this is a product (sign-in, KPI
   events, feedback, deletion, environments) names its `REQ` in the PR block, not in a comment.
5. **No bare `except Exception`.** Catch what the SDK raises and turn it into a clear response.
6. **Pinned dependencies:** `==` in both requirements files, `package-lock.json` committed, GitHub Actions pinned to a major
   (`@v7`). Never the `agent-framework` metapackage.
7. **Nothing unfinished:** no to-do markers (ruff `FIX` enforces it), no placeholder text, no dead code.
8. **Authorship only in the README:** the byline and buttons under the title and `## Author` at the end. `LICENSE` stays the
   unfilled Apache-2.0 template; no author in `pyproject.toml` or `package.json`; never an e-mail.
9. **README** with the common structure of `../_00_MASTER_PROMPTS_PRODUCT/07_README_FINAL.md`: no quick start, no local-run
   instructions, no Codespaces button, no status badges, no em dashes. The product is tried through the published demo.
10. **No agents, prompt agents or workflows defined in Foundry.** Agents and the workflow are code, self-hosted in Container Apps.
11. **`targetScope = 'resourceGroup'`.** `rg-juriscope-stg-swc` and `rg-juriscope-prod-swc` exist; Bicep never creates them.

## Estate checked in phase 0 (2026-10-30, names and states only)

- **Subscription:** pay-as-you-go, no spending limit, `Enabled`, as read from ARM rather than the cached `az account show`. The
  budgets only alert; they never stop spending.
- **GitHub:** public repository with the expected metadata; ruleset `protect-main` active; environments `staging` (branch `main`)
  and `production` (the author as reviewer, tags `v*`); Dependabot alerts and security updates, secret scanning and push protection
  on; Pages by workflow; repository secrets `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `ALERT_EMAIL_ADDRESS`;
  `AZURE_CLIENT_ID` in both environments; no variables yet. CodeQL default setup: phase 1 found it `not-configured` (languages
  detected: `actions`, `python`) and wrote `01-codeql.sh`; phase 5 checks that `javascript-typescript` joins once `web/` exists.
- **Azure, per environment:** resource groups in `swedencentral` with the `project`, `environment` and `owner` tags; runtime
  identities `id-juriscope-stg-swc` and `id-juriscope-prod-swc` with `AcrPull` and `Foundry User`; CI apps
  `gh-product-legal-juriscope-staging` and `-production`, no secrets or certificates, with their federated credentials and the roles
  of the build prompt's `Identity` table. The RBAC Administrator condition allows exactly Storage Blob Data Reader, Storage Blob Data
  Contributor, Key Vault Secrets User and Monitoring Metrics Publisher.
- **Shared base** in `rg-aiplatform-shared-swc` (read, never changed from here): Foundry account `fdry-aiplatform-shared-swc`
  (AIServices S0, local auth off) with project `proj-aiplatform-shared`; `gpt-5-mini` (`2025-08-07`, Global Standard, 100K TPM,
  `NoAutoUpgrade`, guardrail `guardrail-chat`: Hate, Sexual, Violence and Self-harm blocking at medium on prompt and completion,
  Jailbreak, Protected Material text and code) and `text-embedding-3-small` (version 1, Global Standard, 120K TPM, `NoAutoUpgrade`);
  no `gpt-5-nano` (no quota in this subscription, so every model call uses `gpt-5-mini`); registry `craiplatformshared` (Basic, admin user off); workspace `log-aiplatform-shared-swc`; action group
  `ag-aiplatform-shared`; budget `budget-aiplatform-monthly`.
- **Search:** `srch-aiplatform-shared` (Basic, `spaincentral`, same resource group), created by hand on 2026-10-31.
  - **Settings:** `01-azure.sh` brings it to the landing-zone template's settings: system identity, roles only, semantic ranker on
    standard, shared tags, logs to the shared workspace, and Cognitive Services User and OpenAI User for its identity on Foundry.
  - **What spaincentral changes:** the region has no AI enrichment of its own, so built-in skills rely on keyless billing. There are
    no higher-capacity partitions (2 GB, 1 GB of vectors, 15 indexes, shared by P05 to P08). Since 2026-11-01 the app runs in `spaincentral` too, so
    search calls stay in the region and model, Cosmos DB, Key Vault and telemetry calls cross to `swedencentral`.
  - **Phase 2** starts with the build prompt's search precheck; if any check fails, it stops and reports.
- **Quotas:** Cosmos DB region access in `swedencentral` allowed, no accounts yet; no Key Vaults, active or soft-deleted; storage
  accounts 0 of 250 in the region; the global names `kv-juriscope-*`, `stjuriscope*` and `cosmos-juriscope-*` are available.
  **Container Apps managed environments:** the "15" read in phase 0 was wrong; the ARM usages API gives a limit of **1** in
  `swedencentral`, already used by another product. **The author moved Juriscope's Container Apps to `spaincentral` on
  2026-11-01:** `cae-juriscope-stg-spc` and `ca-juriscope-stg-spc`, `cae-juriscope-prod-spc` and `ca-juriscope-prod-spc`. Nothing
  else moves: Cosmos DB, Storage, Key Vault, Application Insights, the identities and the resource groups stay in `swedencentral`.
  Phase 6 read `spaincentral` at 1 of 5 used (another product's staging), so Juriscope's two fit, but the other products' planned
  environments there would fill it (5 of 5). Consumption cores are a per-environment quota, readable only once an environment exists.

## Decisions taken in phase 0

- **Dependencies.** `requirements.txt` holds what the image runs (`app/`). `requirements-dev.txt` adds what runs on the runner or the
  laptop: `ops/` (Blob upload, BOE client, PDF split), `eval/` (`azure-ai-evaluation`, YAML thresholds), `load/` (Locust), tests and
  tooling. This keeps `azure-ai-evaluation` and Locust out of the image. The whole set was installed together on Python 3.12 and
  `pip check` passed.
- **Dependabot** watches `pip` (the `agent-framework-*` packages grouped, so the core and its integrations, which each require a
  minimum `agent-framework-core`, move together) and `github-actions`. Phase 5 added `npm` and phase 6 added `docker`, in the same
  change as the manifests they watch, so Dependabot never looks for a manifest that does not exist yet.
- **CI** has one Python job that runs `make install` and `make check`. Phase 5 adds the web, demo build and axe job; phase 6 adds
  `bicep build` and `lint`.
- **Built-in role definition ids** are the same in every tenant, but they match the GUID check. When the Bicep needs them (phase 6),
  add them to an explicit allowlist in `tests/test_budget.py`, never a blanket exception.

## Decisions taken in phase 1

- **The version store** (`data/boe/`) is built by `ops/boe.py` and documented in `data/README.md`: which blocks are kept, every
  change from the source, the counts and their explanation. The repeal date is the in-force date of the repealing law, not the
  BOE's `fecha_caducidad` (its publication date). `app/models.py` holds only the domain models so far; phases 2 and 4 add theirs.
- **`app/corpus.py` is the domain, all code, no model:** `version_at`, `cite` (applicable version, the current one beside it when it
  differs, the repeal date, "See also"), `references` and `locate`.
  - References: "artículo(s) N", lists and ranges in this Code, among the articles in force on the date asked. "Artículo anterior"
    and "siguiente" resolve among the articles in force when that wording came into force, so article 67 (1996) points to 66, not
    to the later 66 bis. Mentions followed by another law ("de la Ley …") are excluded, and a number lower than an earlier one in
    the same list is a subsection ("178.2 y 3"). Known limits: "artículos anteriores" is not resolved, and two dispositions name
    other laws' articles without that suffix (the repealing disposition, about the 1973 Code, and final disposition one, quoting
    the Ley de Enjuiciamiento Criminal), so their "See also" is wrong.
  - `locate` maps a chunk to articles through 12-word windows, one of them anchored at the chunk's end, that occur exactly once in
    the current text of the Code, so headings, page furniture and notes never decide. On the pypdf text of the consolidated PDF in
    2,000-character chunks with 500 overlap, 492 of 492 chunks of the provisions map (401 to more than one article). The 26 chunks
    of the PDF's index and preamble map to none, which would make the phase 7 rate 95 % over every chunk: **phase 6's
    `ops/corpus.py` leaves the index and preamble out of the parts it uploads.** About 7 ms per chunk.
  - An independent review (subagent) found the "artículo anterior" bug above, the unchecked chunk tail and three untested rules;
    all are fixed, and each new test was shown to fail against the old code.
- **The BOE open-data API answered 500 on every route** on the evening of 2026-10-30. The store was built with `build()` from the
  API's own responses fetched at 14:47 GMT that day; rerun `python -m ops.boe` when the API answers and compare `sha256`.
- **Reuse formula for phase 5:** the conditions give *Fuente de los datos: Agencia Estatal Boletín Oficial del Estado* for verbatim
  copies (the article cards) and *Basado en datos de la Agencia Estatal Boletín Oficial del Estado* for extracted or combined data
  (an answer). The answer footer should use the second.
- **Tooling:** `types-defusedxml` pinned for `mypy --strict`. `make` is not installed on the author's Windows host; sessions run the
  `Makefile` targets' commands with `.venv/Scripts` on the `PATH`. CI runs `make check` as written.

## Decisions taken in phase 2

- **Search precheck passed on 2026-10-31:** `running`, system identity, roles only, semantic ranker standard, shared tags,
  `to-shared-workspace` diagnostics, Cognitive Services User and OpenAI User for its identity on Foundry, and the seven search roles
  of the build prompt's `Identity` table. `guardrail-chat` read: Hate, Sexual, Violence and Self-harm blocking at medium on prompt
  and completion; Prompt Shields jailbreak on; Protected Material text and code on; no indirect-attack (document) shield.
- **The workflow runs directly** (`workflow.run(..., stream=True)`) and `Juriscope.ask` loads and saves the history itself. This is
  the build prompt's fallback, chosen on evidence (ADR-001). `as_agent` drops custom and `executor_invoked` events, and the history
  provider would store intermediate outputs as assistant messages. Phases come from `executor_invoked`, plus the article count
  that `retrieve` yields. Executors are module functions wrapped per build. The edges out of `retrieve` and `verify` route by
  message type.
- **Only answered turns enter the history,** capped at the last ten messages for the agents (ADR-002). The history provider gets a
  `container_client`, because data-plane RBAC cannot create containers.
- **Local Cosmos DB:** `make emulator` runs `juriscope-cosmos` on host ports 8091 and 8090, so it can run beside other products'
  emulators on 8081. `azure-core` refuses bearer tokens over HTTP, so the emulator needs a key, which it does not check.
  **Phase 4 owns the Cosmos client:** a local-only key branch, plus the `juriscope` database and the `history` and
  `conversations` containers, created only in the emulator. For phase 2 they were created once with `create_*_if_not_exists`.
- **Settings** come from the environment or a gitignored `.env`, under the GitHub variable names plus `SEARCH_INDEX` and
  `COSMOS_ENDPOINT`. `chat_model` must have a price in `EUR_PER_MILLION_TOKENS`.
- **Local index:** `make index` (`ops/index.py --target local`) took 1 min 19 s on 2026-10-31. It holds the 746 provisions in force
  (723 articles and 23 dispositions), each its title plus today's text, and all of them map back to themselves through `locate`.
  Embeddings come from `FoundryEmbeddingClient`. The vectorizer uses the account endpoint (`cognitiveservices.azure.com`, a
  supported domain) with the search identity. Size: 11.9 MB, 3.3 MB of vectors, 1 of the service's 15 indexes. Documents
  that fail inside a 207 response fail the run.
- **Known limit, for ADR-003 in phase 6:** repealed provisions cannot be retrieved. The index and `locate` hold today's text, and
  so will the Layout index of the consolidated PDF. So facts dated before a repeal (Book III, 2015) find nothing for the repealed
  provision. Indexing their last versions would need both indexes and `locate` extended.
- **Errors are not refusals** (ADR-005): truncation (`finish_reason` `length`), invalid JSON, a rejected field, a run with no
  outcome, `429` and every other client error raise. `content_filter` covers the filter exception, the filter finish reason, and
  the guardrail's canned "I'm sorry…" text. That text is what the streaming structured-output path returns for a blocked prompt,
  and the SDK wraps it as a `ChatClientException` caused by a `json_invalid` error.
- **Guardrail false positives, measured:** none on 10 general questions, three violent offences or adult sexual assault. Both
  questions on sexual offences against minors were blocked on every attempt (prompt filter, Sexual: high). That is a shared-base
  limit; phase 3's `RESPONSIBLE_AI.md` must state it.
- **Latency against SLA-02 is at risk:** 19 live answers took a median of 10.7 s and 4 of 19 finished under 8 s; *Counsel* is the
  6.0 s median step. `reasoning.effort: "minimal"` is accepted (the build prompt says otherwise) and was faster on four questions.
  **Phase 3 compares `low` and `minimal` on the full suite** before SLA-02 is measured in phase 7 (ADR-010).
- **Measured cost per answered question:** median 0.0046 € (0.0042 to 0.0062 €), the semantic query included at list price.
- **Review:** an independent review (subagent) found eight defects, all fixed with a test each:
  - a truncated or empty reply reported as `content_filter`;
  - model-written citation marks surviving into the answer;
  - an empty query list still searching;
  - a field-level parse error treated as a decline;
  - partial index upload failures passing silently;
  - an unpriced model failing after its tokens were spent;
  - a run with no outcome reported as `content_filter`;
  - unbounded history.

## Decisions taken in phase 3

- **The gate** (`eval/run.py`) runs each case through `Juriscope.ask` with an in-memory history, four cases at a time. It records
  the retrieved articles by wrapping the retriever, and scores with one `@evaluator` check per metric in a `LocalEvaluator`, over
  the cases the metric applies to. Groundedness is `GroundednessEvaluator` with `gpt-5-mini` as judge (`is_reasoning_model`, API
  `2024-10-21`). The judge's context carries each version's in-force date and norm.
- **Item-level metrics:** recall counts a case only when every gold article is in the top five, and citation precision only when
  every citation is in `gold` or `also`. The `errors` threshold (0) is the one addition to the build prompt's table, and a missing
  thresholded metric fails the gate. **The author verified every golden item on 2026-10-31.**
- **Settings:** `SharedBase` holds the shared-base fields, so the gate and `chat_client` need no Cosmos endpoint; `Settings` adds
  Cosmos. In CI, `SEARCH_INDEX` comes from `vars.EVAL_SEARCH_INDEX`.
- **Rate limits arrive inside the stream.** The shared deployment rejects a request with an in-stream error, which the SDK raises as a
  plain `openai.APIError`, not an `APIStatusError`. The SDK cannot retry it, and the framework wraps it in `ChatClientException`.
  The gate retries the whole case after 20, 40 and 80 s, outside the concurrency limit. **Phase 4's 429 → 503 mapping must
  handle this form too**, not only `RateLimitError`. A full run saturates the 100K TPM.
- **Measured against TPM:** the deployment's token counter deducts the prompt only, not `max_completion_tokens`, so the judge's
  60,000-token cap costs no quota.
- **Prompts v2** replaced v1 after the first run: no claims about the sources, only the offence asked about, and nothing copied
  from the question. Effort stays `low`: `minimal` was faster but failed correct refusal and groundedness (ADR-010).
- **Open after phase 3:** full-suite citation precision 0.695 against 0.95, and a canary residual of about 1 in 15. The fix needs a
  decision: *Counsel* receives *Analyst*'s restatement instead of the raw question, and refusal reasons come from a fixed list.
- **CI:** `eval.yml` runs smoke and adversarial on pull requests touching the gated paths, Dependabot excluded, with one updated
  comment. The full suite runs on demand from `main`, in `staging`. Errors in the report are truncated, with host names redacted.
- **Review:** an independent review (subagent) raised 12 findings. Fixed:
  - errors that crashed the run;
  - a canary match that missed case and spacing variants;
  - a missing metric passing silently;
  - NaN judge scores;
  - missing gated paths;
  - raw error text in public comments;
  - five test gaps and four doc mismatches.

  Open for the author: the check is not required by `protect-main`, and the `pull_request` credential sits on the staging deploy
  app.
- **Python module limits:** `eval/run.py` is 118 non-blank lines against its 85. The throttling retry, host redaction and strict
  gate came from live findings and the review. `eval/evaluators.py` is at its 85.

## Decisions taken in phase 4

- **Decision A (approved 2026-10-31), prompts v3.** *Analyst* returns `question` (the lawyer's question, copied as written when it
  stands on its own, resolved when it is a follow-up, never widened) and `scope` (`criminal_code`, `case_law`, `other_law`,
  `not_legal`); *Counsel* receives one message with that question and the articles, never the conversation. `Refusal.scope`
  replaces the free-text `detail`. A first draft let *Analyst* widen the question and citation precision fell to 0.477; the final
  v3 measured, on the full suite, recall 0.966, citation precision 0.737 (v2 0.695), groundedness 0.985, canary 0 of 15, false
  refusal 0.027, one error (*Counsel*'s JSON cut mid-string, not recurring). The PR suites pass (exit 0). v3 was the baseline until v4.
- **Prompt `counsel_v4.md` (2026-10-31), the fix of the required `eval` check.** The PR gate failed on citation precision 0.833
  (the self-defence smoke case cited more than article 20; probes: 21 and 118 in 2 of 4). Over-citation was systematic: true claims from articles the
  question did not need (other offences, other forms or special cases, general rules such as sentencing, civil liability,
  prosecution, legal persons). v4 makes *Counsel* choose the fewest articles that answer the question before writing and names
  those kinds; *Analyst* v3, the brief and `compose` are unchanged (`compose` already cites only verified claims' articles).
  Probe on v3's 15 full-suite failures: v3 5 precise, v4 14. Full suite 18:05 UTC: citation precision 1.000 (59), recall
  0.933 (60, retrieval untouched), groundedness 0.973 (83), version 1.000, correct refusal 1.000, false refusal 0.013 (75),
  canary 0 of 15, errors 0, p50 6.8 s, p95 11.6 s; the gate passes. PR suites, three runs: citation precision 1.000 (6) each;
  exit 0 once, then groundedness 0.889 (the judge reads the raw adversarial question and scored a faithful coercion answer 4 of 5) and
  one transient `APIConnectionError`, which the gate does not retry. Both are open for the author. v4 is the baseline.
  `test_agents_run_the_latest_prompts` holds that each agent loads its newest prompt file, and
  `test_counsel_chooses_the_fewest_articles` the v4 rule. Completeness is not measured (golden `facts` are not scored).
- **Second fix of the required `eval` check (approved 2026-10-31): `analyst_v4.md`, `analyst_v5.md` and code.** CI failed on
  groundedness 0.891 with one `APIConnectionError`, then on canary 1 of 15. Diagnosis (probe, 1 of 3): *Analyst* v3 copied the
  whole question, injection included, into `question`; *Counsel* wrote the phrase into a claim; verification checked only
  article ids. Fixes:
  - `LegalQuery.left_out` lists the passages that are not the legal question. Validation removes them from `question`
    (longest first, word boundaries, any spacing or quote style, passages under 4 characters skipped); an empty question
    becomes `not_legal`. `language` is two lowercase letters, checked in code (Learn lists `pattern` as unsupported in
    structured outputs).
  - `Claim.verified` also drops a claim that shares an 8-character squashed run with a `left_out` passage when the run
    touches a word in neither the Code (`Corpus.words`, every version and title) nor the restated question.
    `LegalQuery.within` keeps only the passages found in the lawyer's latest message: a probe showed *Analyst* v4 copying its
    own instructions into `left_out`, which dropped true English claims and pushed false refusal to 4 of 72.
  - The judge reads `Answer.question` (the restatement, excluded from the JSON). The runner retries `APIConnectionError`
    (not timeouts) like throttling and logs each retry; the API already mapped it to 503.
  - Caps: *Analyst* 800 → 1,600, *Counsel* 3,000 → 4,000 (truncated JSON in live runs; only tokens produced are billed).
  - Figures: PR suites 23:03, 23:05 and 23:06 UTC: passed, passed, failed on recall 0.833 (6; article 249 for
    "estafa básica" outside the first five); every other metric perfect, groundedness 0.986 to 1.000, canary 0. Full suite
    23:24 UTC: recall 0.950 (60), citation precision 1.000 (59), groundedness 0.994 (84), version 1.000, correct refusal
    1.000, false refusal 0.013 (75, the guardrail on intimate images), canary 0 of 15, errors 0, p50 6.3 s; the gate passes.
    Recall sits between v4's 0.933 and v3's 0.966, the evidence that v5's queries are no worse. This column is the baseline.
  - Review (subagent): 2 high, 2 medium and 5 low findings; all fixed except `left_out` covering earlier turns (low, left).
  - Open for the 04 audit: the PR gate's six recall and six citation cases fail it on one miss; options are re-running a
    failing case once before failing, or larger PR suites. English answers sometimes come back in Spanish (no threshold).
- **API (`app/main.py`).** FastAPI's own SSE (`fastapi.sse.EventSourceResponse`, `ServerSentEvent`). The `start` dependency runs the
  ownership check and pulls events until *Analyst* has replied, so failures there are real HTTP statuses; after the first byte an
  `error` event carries the same RFC 9457 body and the request span is marked failed. Mapping: rate limit (`RateLimitError`, or
  exactly `openai.APIError` from the stream) → 503 with the service's `Retry-After` or 20 s; `SearchUnavailableError` (raised by
  `SearchRetriever`), other `AzureError`, connection or timeout → 503; deleted mid-stream → 404; other 4xx from the model and
  `UnusableReplyError` → 502. The 500 handler and the 422 handler also answer problem+json. `conversation_id` is 32 hex or `new`;
  `turn_id` 32 hex. Two live smokes measured the first byte at 1.9 to 9.0 s (six questions); the interface must show
  *Analysing the question* on send.
- **History is saved after the outcome is taken,** so the API writes the record first; `test_deleted_while_answering` holds it.
- **Auth** accepts the role claim typed `role_typ` or `roles`, and the object id claim in its long form or `oid`, because Easy Auth's
  shapes for Entra were not verified against a real header. Phase 7 checks them live.
- **Telemetry:** `telemetry.configure()` runs at import, before the FastAPI app exists, so the Azure Monitor distro can instrument
  it. Without `APPLICATIONINSIGHTS_CONNECTION_STRING`, KPI events go to a console log exporter (the handler from
  `opentelemetry-instrumentation-logging`; the SDK's `LoggingHandler` is deprecated). `create_metric_views()` only: Juriscope has
  no metric instruments of its own. `AnswerAccepted` carries `via`, as `docs/PRODUCT.md` says.
- **Local Cosmos DB:** `COSMOS_KEY` in `.env` (the emulator's published key) makes the API create the database and both containers
  with the 90-day TTL. The emulator accepted the partial update (`add /turns/-`).
- **Decision B:** `04-required-checks.sh` adds `required_status_checks` (`ci`, `eval`, GitHub Actions' app id read with `gh api`) to
  `protect-main`. `eval.yml` lost its `paths` filter, because a path-skipped workflow leaves a required check pending (GitHub
  Docs); a `changes` job decides, a condition-skipped `eval` reports success, and a failed `changes` runs the gate anyway.
  `ci.yml`'s job is now `ci`; phases 5 and 6 either add their steps to it or rerun the script with the new job names.
- **Decision C:** `04-eval-identity.sh` creates `gh-product-legal-juriscope-pull-request` (pull-request credential only; Foundry
  User on the project, Cognitive Services OpenAI User on the account, Search Index Data Reader on the `jur-articles-local` index,
  a scope Learn documents for the CLI), sets `EVAL_CLIENT_ID`, removes the staging app's pull-request credential and deletes the
  repository `AZURE_CLIENT_ID`. `01-azure.sh` no longer recreates either.
- **The gate's retry** now covers `RateLimitError` and in-stream errors only; a timeout is reported as an error.
- **Review:** an independent review (subagent) found no high-severity issue and 12 findings. Fixed: history orphaned by a failed or
  raced record write; a deletion mid-stream reported as 503; the gate failing open when `changes` fails; Easy Auth claim shapes;
  timeouts counted as rate limits; permanent model 4xx sent with `Retry-After`; unconstrained ids; free-text `turn_id`; 422 not
  problem+json; the fake's not-found semantics. Left: the 2 MB item limit (ADR-002) and the all-zero trace id in unit tests
  (phase 7 checks trace ids in Application Insights).
- **Python module limits:** `app/main.py` is 187 non-blank lines against its 140: problem responses for three dependencies on both
  sides of the first byte, and the pre-stream buffering. `app/workflow.py` is at 143 against 140. Totals stay within budget.
  After the second `eval` fix: `app/models.py` 110 against 80 (the `left_out` removal, the claim check and `within`),
  `app/corpus.py` 91 against 90, `app/doubles.py` 36 against 35, `eval/run.py` 119 against 85; moving the text checks to their
  own module is left for the 04 audit, because it would change code after the measured runs.

## Decisions taken in phase 5

- **`web/` copies Folium's client** (the first `product-*` with `web/`), changing only the name, logo, suggestions and logic:
  React 19.3.1, TypeScript 7.0.2 (`tsc --noEmit` passes, no fallback to 6.x), Vite 8.3.5, `lucide-react` 1.65.0, `react-markdown`
  10.1.0 (as in the sibling products), `@fontsource/inter` 5.3.0. `api.ts` holds the types, the SSE parser and the demo replay;
  `Article.tsx` the article and refusal cards; `main.tsx` the shell. TypeScript 422 of 799 lines.
- **The interface** shows *Analysing the question* the moment a question is sent (19 to 38 ms, measured), then each `phase` event
  as a progress line; the article card shows the version badge, six clamped lines with *Show full article*, both versions side by
  side when the date of the facts selects an older one, "See also", the boe.es link and *Fuente de los datos: Agencia Estatal
  Boletín Oficial del Estado* (verbatim copy). The answer footer uses the API's notice, *Basado en datos de la Agencia Estatal
  Boletín Oficial del Estado. Texto consolidado de carácter meramente informativo.*, plus the update date and "For the firm's
  lawyers. Not legal advice." A stream that ends without an outcome shows "The answer was interrupted".
- **Demo mode** reads `web/fixtures/*.json` at build time; `?run=<id>` replays a run on load (shareable, and how the axe job
  reaches each recorded state). Fixtures come from `ops/record.py`, which records SSE events with their timings from a running API
  (`RECORD_AUTH_HEADER` carries the auth header, never the command line), checks that every turn ended in an answer or a refusal,
  replaces the conversation and turn ids with the run id, and deletes the recorded conversation. The phase 5 fixtures were
  recorded on 2026-11-01 from the local API (emulator, shared models, `jur-articles-local`); **phase 8 re-records them from
  staging with the same command.** One recording of S4's follow-up, worded "¿Y si es agravada?", cited article 248 instead of 250, so
  the run asks "¿Y si la estafa es agravada?"; S4's follow-up then cited 250 only, not 131 (limitation).
- **`app/main.py` serves `web/dist`** at `/` when it exists (phase 6's image builds it); the API routes match first.
- **CI:** the web, demo and axe steps are inside the `ci` job, so the required checks stay `ci` and `eval` and
  `04-required-checks.sh` need not run again. axe (`@axe-core/cli` 4.14.0, a pinned dev dependency, with the runner's
  chromedriver because the package's own targets Chrome 152) scans the empty state and every recorded run after 25 s, and S1
  mid-stream after 3 s. Dependabot watches `npm` in `/web`.
- **Chrome's `scrollIntoView` now returns a Promise:** an effect that returns it crashes React on cleanup, so effects use `void`.
- **CodeQL default setup** analyses `actions` and `python`; GitHub Docs do not say whether a new language joins by itself, so
  `05-codeql-web.sh` adds `javascript-typescript` after the merge if it is missing.
- **Review:** an independent review (subagent) raised 1 high, 5 medium and 5 low findings. Fixed: raw 32-hex ids in the fixtures,
  the green "done" text under 4.5:1, `aria-busy` silencing the progress status and a `log` region reading whole articles, missing
  `lang` on answers, the open mobile drawer leaving the thread focusable (`inert`, Escape), a stream ending without an outcome,
  recorder failures leaving conversations behind, the auth header on the command line, a missing `web/dist`, the mid-stream axe
  pass, a rejected clipboard write, a stale `?run=` after *New chat*, and the empty search result. Left: focus is not returned to
  the menu button when Escape closes the drawer.

## Decisions taken in phase 6

- **Bicep** (`infra/`, 465 of 490 lines): `main.bicep` and four modules (`data`, `monitor`, `app`, `roles`), one parameter file per
  environment reading the deploy values from the environment (`readEnvironmentVariable`).
  - The runtime identity is `existing`; the Bicep reads the shared search service (its identity, for Storage Blob Data Reader on
    `corpus`) and the workspace id only. The registry login server and the Foundry and search endpoints come from the repository
    variables, so no CI identity needs a read role on the registry.
  - Built-in role ids are written without hyphens in `modules/roles.bicep` (as in Folium), so the identifier scan stays strict
    without an allowlist.
  - API versions checked against the ARM provider listings and the Bicep 0.48.1 type index (linter `use-recent-api-versions` at 730
    days): App 2026-07-01, DocumentDB 2026-03-15, Storage 2026-06-01, Key Vault 2026-02-01, Insights components 2020-02-02,
    workbooks 2023-06-01, scheduled query rules 2026-03-01, metric alerts 2026-01-01, budgets 2026-06-01, action groups 2023-01-01.
    Two `#disable-next-line use-recent-api-versions` directives remain: `diagnosticSettings@2021-05-01-preview` (the newest) and the
    Application Insights daily cap, `components/pricingPlans@2017-10-01`.
  - Container Apps logs go to the shared workspace through a diagnostic setting (`destination: azure-monitor`), not shared keys.
  - Liveness is a TCP probe, so a Cosmos DB outage marks replicas not ready instead of restarting them.
- **Easy Auth is `AllowAnonymous`; the app authorizes** (ADR-006). `RedirectToLoginPage` would answer an API call without a session
  with a 302, not the 401 REQ-07 requires. The web client now sends a 401 to `/.auth/login/aad` (one line in `api.ts`).
  Audiences are `api://<client id>` and the client id, issuer v2: **the phase 7 and 8 scripts must set the sign-in app's
  `api.requestedAccessTokenVersion` to 2**, and **`08-production.sh` must give the production CI principal `Juriscope.User`**,
  because `release.yml`'s smoke test calls `/api/meta`.
- **`MODEL_DOUBLE=true`** (`Settings.model_double`) makes the app use `ModelDouble`; `load-test.yml` sets it on the `loadtest`
  revision only.
- **`ops/corpus.py`** splits at body headings (a whole line `LIBRO …` or `TÍTULO …`; the PDF's index lines carry dots and titles) and
  starts at *TÍTULO PRELIMINAR*, leaving out the index and the preamble. Measured 2026-11-01: pages 11–117 (378,457 characters) and
  118–207 (308,498); 459 of 459 `pypdf` chunks (2,000/500) map through `locate`. The PDF's SHA-256 is blob metadata: an unchanged PDF
  uploads nothing.
- **`ops/index.py --target staging|production`** writes the data source (search identity, blob soft-delete detection), the skillset
  (Layout, split, embedding, index projections, `AIServicesByIdentity`) and the indexer, runs it and waits; implemented and
  unit-checked only, first run in phase 7. It now reads `SharedBase`, so no Cosmos endpoint is needed.
- **Image:** `docker build` on 2026-11-01 (369 MB, user 1000); the container with the emulator and the model double answered
  `/healthz` 200, `/` 200 (the built web) and `/api/me` 401.
- **Workflows:** `deploy.yml` (Buildx, `az acr login`, `what-if`, revision by digest, corpus and index, canary health check, smoke,
  artifact `image-<sha>`), `release.yml` (artifact digest and `load-test` status, canary 10 % with an Application Insights check,
  rollback), `load-test.yml`, `pages.yml`. Actions are pinned to majors only, because a SHA pin needs a `#` comment for its version.
  The Bicep step is inside the `ci` job, so `04-required-checks.sh` need not run again. Dependabot watches `docker`.
- **Cost in Spain Central** is about 42 % above Sweden Central for Container Apps. Production at rest is about 15.5 € a month, and the
  all-in cost per question at 350 questions is 0.049 to 0.051 € against the 0.05 € SLO (`docs/cost.md`, ADR-008). Phase 7 measures
  CPU and memory under load to decide whether 0.25 vCPU / 0.5 GiB is enough.
- **`what-if` on 2026-11-01**, with the author's identity and placeholder secrets: both resource groups show 22 creates, the
  existing identity ignored, and 4 role assignments `Unsupported` (their names depend on runtime principal ids). There were no
  modifications and no deletions. Rerun after the review fixes: the same.
- **Review:** an independent review (subagent) found 2 high, 4 medium and 4 low findings; all fixed:
  - the projection read the embedding and the headings from the wrong skill output paths, so vectors and headings would have been
    null;
  - the canary check and smoke test ran after the federated token expired, so every release would have rolled back. They now have
    their own sign-ins, and the smoke test runs on the canary label before promotion;
  - the rollback now reactivates the previous revision;
  - the load-test status names the digest it tested, and `release.yml` requires that digest;
  - corpus and index are retried while new roles propagate;
  - an extra sign-in in `load-test.yml`;
  - the model names come from the repository variables in Bicep too;
  - uvicorn keep-alive is 75 s, behind the Envoy pool;
  - `deploy.yml` runs only from `main`.

  Left for phase 7: the Key Vault role may not have propagated when the first revision resolves the secret; rerun the workflow,
  or let `07-staging.sh` grant Key Vault Secrets User to the runtime identity in advance.

## Verified names (installed wheels, 2026-10-30)

Installed together: `agent-framework-core` 1.23.0, `agent-framework-foundry` 1.15.0 (it brings `agent-framework-openai` 1.17.0 and
`azure-ai-projects` 2.7.0), `agent-framework-azure-cosmos` 1.0.0b261015, `azure-search-documents` 12.0.0, `azure-ai-evaluation`
1.18.10, `azure-monitor-opentelemetry` 1.8.11. Re-check a name here before using it; phases add rows as they verify more.

| Purpose | Name |
|---|---|
| Agents | `agent_framework.Agent(client, instructions=None, *, name=, default_options=, context_providers=, middleware=)`; `Message`. `ChatAgent` and `ChatMessage` no longer exist |
| Workflow | `agent_framework.WorkflowBuilder(*, start_executor=, name=, max_iterations=, output_from=)`: the start executor is a required constructor argument; edges with `add_edge`, `add_switch_case_edge_group`, `add_multi_selection_edge_group`; `@executor`, `AgentExecutor`, `WorkflowEvent` |
| Workflow as an agent | `Workflow.as_agent(name=None, *, description=, context_providers=)` → `WorkflowAgent`; `WorkflowAgent.create_session(*, session_id=)`; `Workflow.run(message, *, stream=False, include_status_events=False)` |
| Chat client | `agent_framework.foundry.FoundryChatClient(*, project_endpoint=, model=<deployment name>, credential=)` |
| History | `from agent_framework.azure import CosmosHistoryProvider` or `from agent_framework_azure_cosmos import CosmosHistoryProvider`; **`agent_framework.azure_cosmos` does not exist**. `CosmosHistoryProvider(source_id="azure_cosmos_history", *, load_messages=True, store_outputs=True, store_inputs=True, store_context_messages=False, endpoint=, database_name=, container_name=, credential=, cosmos_client=, container_client=)` |
| Content filter | `agent_framework.exceptions.ChatClientContentFilterException` (base, no filter details); `agent_framework.openai.OpenAIContentFilterException`, its subclass, carries `.content_filter_code` and `.content_filter_result` |
| Evaluation | `agent_framework.LocalEvaluator`, `evaluator`, `evaluate_agent`, `evaluate_workflow`; `azure.ai.evaluation.GroundednessEvaluator`, `RelevanceEvaluator` |
| Telemetry | `azure.monitor.opentelemetry.configure_azure_monitor`; `agent_framework.observability.enable_instrumentation`, `create_resource`, `create_metric_views` |
| Search | `azure.search.documents.aio.SearchClient`; `azure.search.documents.models.VectorizableTextQuery` |
| Workflow events (2026-10-31) | `WorkflowBuilder(start_executor=, output_from=, intermediate_output_from=)`; `WorkflowAgent` forwards only `output`, `intermediate`, `data`, `request_info`; `executor_completed.data` is the sent messages plus the yielded outputs; a message reaches only targets whose handler accepts its type; an executor's exception leaves `workflow.run` with its own type |
| Agent executor (2026-10-31) | `AgentExecutor(agent, *, id=)`; `AgentExecutorRequest(messages=, should_respond=)`; `AgentExecutorResponse.agent_response`, `.full_conversation` (input plus the reply); in streaming workflows the agent streams and its updates are hidden unless the executor is listed as output |
| Responses (2026-10-31) | `AgentResponse.value` (None for empty text), `.finish_reason` (a `str` NewType), `.usage_details["input_token_count" / "output_token_count"]`; options `response_format`, `reasoning`, `max_tokens` (sent as `max_output_tokens`), `store`; `FoundryChatClient.client` is an `AsyncOpenAI` (`with_options(timeout=)`); a 400 `content_filter` becomes `OpenAIContentFilterException` (needs a `BadRequestError`), anything else a `ChatClientException` chained `from` the cause |
| Doubles and history (2026-10-31) | `BaseChatClient._inner_get_response(*, messages, stream, options)` returning `ResponseStream(updates, finalizer=)` or its `get_final_response()`; `HistoryProvider.get_messages(session_id)` and `save_messages(session_id, messages)`; `InMemoryHistoryProvider` keeps messages in session state only |
| Embeddings (2026-10-31) | `agent_framework.foundry.FoundryEmbeddingClient(project_endpoint=, model=, credential=)`; `await get_embeddings(texts)` → items with `.vector` |
| Evaluation (2026-10-31) | `EvalItem(conversation, *, context=, expected_output=)`; `@evaluator` passes only `query`, `response`, `expected_output`, `expected_tool_calls`, `conversation`, `tools`, `context`; `LocalEvaluator(*checks).evaluate(items, eval_name=)` → `EvalResults.passed`, `.total`, `.items[].is_passed`, `.input_text` (scores are pass or fail, never a mean); `GroundednessEvaluator(model_config, *, threshold=3, credential=, is_reasoning_model=)` returns `groundedness` (1–5, NaN when unparsed); `AzureOpenAIModelConfiguration(azure_endpoint=, azure_deployment=, api_version=)`; `openai` 3.41.0 uses `httpx2` |
| API (2026-10-31) | `fastapi.sse.EventSourceResponse` (`response_class=` on an async-generator route), `ServerSentEvent(event=, data=)`; `azure.cosmos.aio.ContainerProxy.patch_item(item, partition_key, patch_operations)`, `query_items(query, partition_key=)`, `read()`; `azure.cosmos.exceptions.CosmosResourceNotFoundError`; `CosmosClient(url, credential, connection_timeout=)`; `opentelemetry.instrumentation.logging.handler.LoggingHandler`; `opentelemetry.sdk._logs.export.ConsoleLogRecordExporter`; FastAPI's `TestClient` returns `httpx2.Response` |
