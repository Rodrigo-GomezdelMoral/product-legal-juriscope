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
  (phase 3), `04-eval-identity.sh` and `04-required-checks.sh` (phase 4), `05-codeql-web.sh` (phase 5, after its merge), `07-staging.sh`
  (phase 7: sign-in app `product-legal-juriscope-staging` with v2 tokens, `Juriscope.User` for the author and the staging CI
  principal and a `user_impersonation` scope pre-authorized for the Azure CLI; `AUTH_CLIENT_SECRET` and `AUTH_CLIENT_ID` in
  `staging`; `DEPLOY_ENABLED=true` **at repository level**, because a job-level `if` is evaluated before environment variables
  exist; a temporary Key Vault Secrets User on the resource group for the first revision, removed after it; `deploy.yml` on
  `main`; the redirect URI; Search Index Data Reader on `jur-articles-stg` for the pull-request identity; `EVAL_SEARCH_INDEX`), `07-live-runs.sh`
  (phase 7: `load-test.yml`, the full `eval.yml`, the browser sign-in; results to `%TEMP%\juriscope-p07`).
  `08-production.sh` (phase 8: sign-in app `product-legal-juriscope-production` like staging's, `Juriscope.User` for the author and the
  production CI principal, `AUTH_CLIENT_SECRET` and `AUTH_CLIENT_ID` in `production`, a temporary Key Vault Secrets User for the first
  revision; run again after v1.0.0 for the callback, the role's removal, the browser check and a summary in `%TEMP%\juriscope-p08`;
  `DEPLOY_ENABLED` is not read by `release.yml`).
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
   and in a GitHub environment secret (ADR-006). In the workflows, `AZURE_TOKEN_CREDENTIALS: AzureCliCredential` pins
   `DefaultAzureCredential` to the `azure/login` session: a hosted runner's metadata endpoint can answer without a token and stop
   the chain at `ManagedIdentityCredential` (deploy run of 2026-11-02, "No token received").
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
    no higher-capacity partitions (2 GB, 1 GB of vectors, 15 indexes, shared). Since 2026-11-02 the apps run in `francecentral` (ADR-014),
    so search calls cross to `spaincentral` and model, Cosmos DB, Key Vault and telemetry calls to `swedencentral`.
  - **Phase 2** starts with the build prompt's search precheck; if any check fails, it stops and reports.
- **Quotas:** Cosmos DB region access in `swedencentral` allowed, no accounts yet; no Key Vaults, active or soft-deleted; storage
  accounts 0 of 250 in the region; the global names `kv-juriscope-*`, `stjuriscope*` and `cosmos-juriscope-*` are available.
  **Container Apps managed environments:** the "15" read in phase 0 was wrong; the ARM usages API gives a limit of **1** in
  `swedencentral`, already used in the subscription. **The author moved Juriscope's Container Apps to `spaincentral` on
  2026-11-01:** `cae-juriscope-stg-spc` and `ca-juriscope-stg`, `cae-juriscope-prod-spc` and `ca-juriscope-prod` (apps renamed in phase 7). Nothing
  else moves: Cosmos DB, Storage, Key Vault, Application Insights, the identities and the resource groups stay in `swedencentral`.
  Phase 6 read `spaincentral` at 1 of 5 used, so Juriscope's two fit. Consumption cores are a per-environment quota, readable only once an environment exists.
  **Superseded on 2026-11-02 (ADR-014):** one environment per product, `cae-juriscope-env`, in `rg-juriscope-prod-swc`, in
  `francecentral`; see the section *Container Apps environment* below.

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
- **Local Cosmos DB:** `make emulator` runs `juriscope-cosmos` on host ports 8091 and 8090, so it can run beside another
  emulator on the default 8081. `azure-core` refuses bearer tokens over HTTP, so the emulator needs a key, which it does not check.
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
  so will the staging and production indexes of the PDF. So facts dated before a repeal (Book III, 2015) find nothing for the
  repealed provision. Indexing their last versions would need both indexes and `locate` extended.
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

- **`web/` uses the common chat client shell**, changing only the name, logo, suggestions and logic: React 19.3.1, TypeScript
  7.0.2 (`tsc --noEmit` passes, no fallback to 6.x), Vite 8.3.5, `lucide-react` (1.59.0 since the web parity change below),
  `react-markdown` 10.1.0, `@fontsource/inter` 5.3.0. `api.ts` holds the types, the SSE parser and the demo replay;
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
  - Built-in role ids are written without hyphens in `modules/roles.bicep`, so the identifier scan stays strict
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
  (split, embedding, index projections, `AIServicesByIdentity`) and the indexer, runs it and waits. spaincentral rejects the
  Layout skill, so the indexer extracts the PDF text itself (ADR-003). It now reads `SharedBase`, so no Cosmos endpoint is needed.
- **Image:** `docker build` on 2026-11-01 (369 MB, user 1000); the container with the emulator and the model double answered
  `/healthz` 200, `/` 200 (the built web) and `/api/me` 401.
- **Workflows:** `deploy.yml` (Buildx, `az acr login`, `what-if`, revision by digest, corpus and index, canary health check, smoke,
  artifact `image-<sha>`), `release.yml` (artifact digest and `load-test` status, canary 10 % with an Application Insights check,
  rollback; since ADR-015 the `load-test` status is skipped when only `web/`, `docs/`, `.github/` or Markdown changed), `load-test.yml`, `pages.yml`. Actions are pinned to majors only, because a SHA pin needs a `#` comment for its version.
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

## Phase 7 live evidence (first session, 2026-11-01, times in UTC from Azure; the laptop clock runs about 2 min 10 s fast)

- **Staging as deployed:** revision `r4-1` (deploy runs of 12:11 and 12:15, digest of `c074a7e`), 0.5 vCPU / 1 GiB, min 0,
  max 2, HTTP rule at 10 concurrent requests, traffic pinned by revision name (so `load-test.yml`'s revision gets 0 %). The
  `auth-client-secret` secret is a Key Vault reference resolved with the runtime identity; the temporary Key Vault Secrets User on
  the resource group is gone and the vault-scoped one (Bicep) remains. Cosmos DB: `Continuous7Days` on serverless (RPO 15 min
  holds); both containers `defaultTtl` 7,776,000 (REQ-10).
- **REQ-07 and Spoofing, live (12:20):** no session → 401 problem+json on `/api/me`, `/api/conversations` and `/api/meta`; an
  invalid bearer → 401; a forged `X-MS-CLIENT-PRINCIPAL` (plus `-ID`) without a token → 401; the same forged header with a valid
  token → 200 as the token's user, the forged name ignored (Easy Auth replaces the header). Unknown conversation id → 404, and its
  `trace_id` is the request's `operation_Id` in Application Insights. 403 has no live check: every principal at hand holds the role
  (test only).
- **Easy Auth claim shapes:** a v2 user token from the Azure CLI (scope `user_impersonation`) carries `roles` and `oid`, which the app
  accepts; but the principal's `name_typ` claim is absent, so `/api/me` returned an empty name and the UI showed "Signed out".
  **Fixed:** `app/auth.py` falls back to the `name` claim; `test_api.py`'s Entra principal now uses the SOAP `name_typ` and fails
  without the fix. Deploys with the phase 7 merge.
- **Every *Must* in the browser** (headless Chromium, the deployed web, every request carrying the author's bearer token; 12:22 to
  12:24; screenshots outside the repository): S1 English reckless homicide → answer in English, 1 article card (version in force since
  2022-09-15 · BOE-A-2022-14965), 2 boe.es links, "See also" 1, *Show full article* expands, 👍 and copy sent; S2 art. 139 in
  May 2014 → both versions side by side ("Applies on 2014-05-15" 1996 wording beside "In force today" 2015); S3 Supreme Court
  question → refusal card (case law); S4 limitation of fraud → 3 cards, follow-up "¿Y si la estafa es agravada?" → 2 cards on
  aggravated fraud through history; reload, resume from the sidebar (2 turns, 5 cards), delete with confirmation, gone after reload. Time from
  send to the final state: 9.8, 10.4, 8.3 and 12.9 s for answers (11.4 s on a first attempt), 3.7 s for the refusal;
  *Analysing the question* within 10 to 27 ms. **Not yet proven:** the interactive code-flow sign-in (ADR-006), in
  `07-live-runs.sh` step 4.
- **KPI events in KQL:** `QuestionAsked` 6, `AnswerDelivered` 6 (outcome, claims, `dropped_claims` 0, `cost_eur`),
  `AnswerAccepted` 2, `FeedbackGiven` 1, all with `user_hash` and `turn_id`, no text.
- **Sampling defect, fixed:** `azure-monitor-opentelemetry` 1.8.11 defaults to a rate-limited sampler of 5 traces per second
  (`_utils/configurations.py`); the page reload's burst lost `GET /api/conversations`, the conversation read and the `DELETE`, and
  the workbook's `count()` tiles would undercount. `telemetry.configure` now passes `sampling_ratio=1.0`. Logs (KPI events) were
  never sampled.
- **Latency per step** (spans, partly sampled): *Analyst* 2.5 s, `retrieve` p50 0.83 s (search call 0.6 s, same region), *Counsel*
  (`draft`) p50 5.2 s, p95 7.5 s, `verify` 4 ms. Counsel alone nearly uses the 8 s of SLA-02, so SLA-02 is at risk before the load
  test runs.
- **Cold start:** the first request after scaling to zero took 30.1 s, the next ones 0.04 to 0.06 s (ADR-008's warm replica).
- **Workbook** `Juriscope KPIs, SLOs and health (stg)`, deployed with the four tags: 10 of 11 queries run. **K4 was broken**:
  `startofweek(timestamp, 1)` labels the *next* Sunday, and a column used in the same `extend` that defines it is rejected
  (BadArgumentError). **Fixed** in `infra/modules/monitor.bicep` (Monday weeks: `startofweek(timestamp - 1d) + 1d`, two
  `extend`s); the fixed query runs.
- **Alerts:** `alert-juriscope-stg-5xx` (metric), `-availability` and `-latency` (log, every 15 min), all disabled, as designed;
  plus the *Failure Anomalies* smart detector that Application Insights creates by itself (free, not in Bicep).
- **Cost per question (measured):** answers 0.0046 to 0.0060 € (median 0.0052 €, 5), refusal 0.0007 €; the workbook tile gives
  0.0211 € all-in in staging (6 questions, 0.1 € standing). Production at 350 questions: (15.5 + 350 × 0.0052) ÷ 350 ≈ **0.0495 €**,
  inside the 0.05 € SLO with almost no margin.
- **CPU and memory before the load test** (one user, real model): CPU max 0.065 vCPU, working set max 463 MB (0.43 GiB). 0.25 vCPU
  / 0.5 GiB would leave about 70 MB of memory at one user: the size-down looks unsafe, pending the load test's peak.
- **PR suites on `jur-articles-stg`, local run with the author's identity (12:32):** passed; recall 1.000 (6), citation
  precision 1.000 (6), version 1.000 (2), correct refusal 1.000 (2), false refusal 0 (8), canary 0 (15), groundedness 0.971 (17),
  errors 0; p50 8.1 s, p95 12.3 s at four concurrent; median 0.0052 €. The full suite runs in `eval.yml` (`07-live-runs.sh`).
- **Restore drill (RTO):** `az cosmosdb restore` of `cosmos-juriscope-stg-swc` to `cosmos-juriscope-stg-drill` (swedencentral) at
  12:24:14.5, started 12:31:30, `Succeeded` 12:42:36 (11 min 6 s); local auth was enabled on the restored account only, and a
  read-only key read 3 conversations and 4 history messages at 12:43:47: **12 min 17 s from the decision to readable data**,
  against the 4 h RTO. The restored state matched the live one about 25 s before the requested point (the conversation started at
  12:23:51 was missing), well inside the 15 min RPO. Not rehearsed: pointing the app at a restored account (the Bicep's Cosmos
  account name and a redeploy); `OPERATIONS.md` must say so. The restored account was then deleted. Restores of continuous
  backups bill per GB restored, so a few KB cost nothing measurable.
- **Mapping rate:** 474 of 474 chunks of `jur-articles-stg` map to an article (100 %), measured before this session.
- **Advisor (2026-11-01):** nothing on the staging resource group. Shared base: registry geo-replication and Premium
  (ADR-012), a second search replica (ADR-007), a newer Azure OpenAI API version on the Foundry account (the SDK picks it); the
  subscription-level Service Health alert is outside this repository. The staging resources were created at 11:16, so Advisor
  may not have assessed them yet: read it again before closing.
- **Cost Management:** no rows for `rg-juriscope-stg-swc` yet (data lags up to a day); the shared base shows search 1.34 € and
  models 8.26 € on 2026-10-31.
- **DORA (staging):** 3 `deploy.yml` runs with a result, 1 failed (11:37, Layout rejected) and restored by PR #10 at 12:11
  (34 min); lead time of PR #10 12 min (opened 11:59, deployed 12:11).
- **Open for the second session** (after the author's `07-live-runs.sh`, results in `%TEMP%\juriscope-p07`):
  - SLA-02 p95, error rates, replicas, CPU and memory from `load/` (`real_stats.csv`, `platform.tsv`), and the size-down decision
    against the cost-per-question SLO (expected: keep 0.5 vCPU / 1 GiB, given 0.43 GiB at one user);
  - the full suite on `jur-articles-stg` from `eval/`, compared with the local index's 23:24 baseline in `docs/evaluation.md`;
  - the browser sign-in answers (`browser.txt`), Advisor again, Cost Management by tag;
  - the docs: `OPERATIONS.md` (load tests, restore drill and RTO, DORA, `DEPLOY_ENABLED` at repository level, alerts),
    `PRODUCT.md` (`DEPLOY_ENABLED`), `cost.md`, `THREAT_MODEL.md` proofs, ADR-006 (Key Vault reference proven), ADR-008 (cold
    start 30.1 s), `evaluation.md`; then the phase block and `publish-staging.sh`.
  - **Decision for the author, SLA-02:** *Counsel* alone takes p50 5.2 s and p95 7.5 s, so 95 % under 8 s is out of reach with
    `gpt-5-mini` at `low` effort whatever the rest does. Options: (a) both agents at `minimal`, which failed the gate with v2
    prompts and would need a full-suite run with v4/v5; (b) a non-reasoning model for *Counsel*, a new deployment in the shared base
    (author's change, gate against the baseline); (c) restate SLA-02 from evidence, for example 95 % under 15 s to the final event,
    with the progress line inside 0.1 s, and keep the latency SLO in step. Recommended: (c) now, (a) as a measured experiment
    later, because a 12 s answer against 30 to 75 minutes of manual research does not move K1, and the prompt forbids promoting on a
    missed SLA.

## Phase 7 second session (2026-11-02, from the author's `07-live-runs.sh` of 2026-11-01; times in UTC)

- **`load-test.yml` run 41331036489** (digest of `c074a7e`): load revision `load1-1` 17:22:42–17:57:49, real model on the stable
  revision `r4-1` 17:57:51–17:59:51. Asks, p95, failed: normal (5 users, 3 min) 79, 5.1 s, 0; peak (20, 2 min) 203, 7.7 s, 0; soak
  (5, 10 min) 266, 1.4 s, 0; stress (5 to 100 users, 20 min) 4,159, p50 2.3 s, p95 10 s, 0 failed (never reached 5 % errors; CPU
  saturated from about 70 users, readiness and liveness probes timing out 17:55–17:57); real model (3 users, 2 min) 14, p50 9.7 s,
  p95 37 s, 0. Red only on the SLA-02 gate. No 429 in any dependency during the whole run.
- **Why 37 s:** a cold start of the stable revision, not the model. `r4-1` had been idle for the 35 minutes of the load revision's
  scenarios and was at zero replicas. ContainerAppSystemLogs: KEDA scaled it 0 → 1 at 17:57:51.7 (the first ask), image pull at
  17:58:06.8, container started 17:58:07.9; Application Insights: the three first asks reached the app at 17:58:16.9 (25.5 s after
  Locust sent them) and took 10.3, 11.3 and 10.3 s, so 36 to 37 s at the client. With 14 samples, those 3 are the p80 and above.
  Server-side, all 15 real asks: 7.2 to 13.7 s, median 9.5 s, p95 13.7 s. Spans (11 sampled workflows): workflow p50 8.4 s, max
  11.5 s; *Analyst* p50 2.7 s, p95 6.5 s; `retrieve` p50 0.69 s, p95 1.2 s (search 0.46 s); *Counsel* p50 4.1 s, p95 8.0 s.
  Cost per answer median 0.0051 € (15).
- **Size:** CPU and memory maxima per revision in the window: `load1-1` 0.51 vCPU and 0.53 GiB (stress), 0.22 vCPU and 0.40 GiB
  at the peak scenario; `r4-1` 0.08 vCPU and 0.40 GiB at 3 users on the real model. **Kept 0.5 vCPU / 1 GiB** (ADR-008, `cost.md`).
- **`eval.yml` full suite, run 41334415716** (18:11, `jur-articles-stg`, 110 cases): passed. Recall@5 0.917 (60), citation
  precision 1.000 (58), version 1.000 (15), correct refusal 1.000 (20), false refusal 0.027 (75), canary 0 (15), groundedness 0.994
  (82), answer language 0.988 (82), errors 0; p50 8.4 s, p95 12.3 s at four concurrent; median 0.0049 €. The judge's calls met 34
  `RateLimitError` 429s on the shared `gpt-5-mini` and retried them; no case failed.
- **Rename (author's decision):** the apps become `ca-juriscope-stg` and `ca-juriscope-prod` (no region code, like the other
  products); environments stay `cae-juriscope-<env>-spc`. `infra/modules/app.bicep`, the three workflows, `OPERATIONS.md`,
  `architecture.md`, `07-staging.sh` (`SKIP_DEPLOY=1` deletes `ca-juriscope-stg-spc` and drops its callback) and `07-live-runs.sh`.
  The deploy after the phase 7 merge creates the new app; the browser sign-in (`ONLY=browser`) moves to after it.
- **SLA-02, author's decision of 2026-11-02 (ADR-013):** 95 % under 15 s to the final event plus *Analysing the question* within
  0.1 s (browser); latency SLO p95 < 13 s (the old 2 s gap). `load-test.yml` waits for `/healthz` 200 on the stable revision, then
  runs the real-model scenario 5 minutes (`SHAPES["real"] = (3, 300)`, about 35 asks); its gate is `-lt 15000`. Moved with it: the
  workbook tile and the latency alert in `monitor.bicep` (13 and 15), `release.yml`'s canary p95 (13,000 ms), `PRODUCT.md`,
  `OPERATIONS.md`, ADR-004, 008 and 010, and the header of `07-live-runs.sh`.

## Phase 7 close (2026-11-02)

- **Also fixed:** `load-test.yml`'s replicas, CPU and memory step printed empty values (`max()` over a list with nulls); the query
  is now `max(timeseries[0].data[?maximum].maximum)`, checked against the 2026-11-01 window (2 replicas, 0.51 vCPU, 0.53 GiB).
  Per revision, the load revision reached 2 replicas in soak and stress, 1 in normal and peak.
- **Docs:** `OPERATIONS.md` (load-test table, restore drill and RTO, DORA, `DEPLOY_ENABLED` at repository level, alerts checked
  disabled), `THREAT_MODEL.md` proofs, ADR-006 (Key Vault reference proven: `r4-1` and the later load revision resolved it, the
  second with only the vault-scoped role; the browser code flow pending), `evaluation.md` (staging column against the baseline),
  `cost.md` (Cost Management), ADR-013. `PRODUCT.md` has no variables table, so `DEPLOY_ENABLED` is documented in `OPERATIONS.md`.
- **Advisor (2026-11-02):** staging: *increase the minimal replica count* (Medium), justified by ADR-008 (staging scales to zero;
  production has one warm replica). Shared base: the same four as before (ADR-007, ADR-012; the API version is the SDK's).
- **Cost Management (2026-11-02):** `rg-juriscope-stg-swc` 0.40 € month to date, Cosmos DB 0.399 € (the load test), no
  Container Apps charge yet. Grouping by two tag keys returns `None` for the second one, and the API then answered 429: read
  `environment` alone in phase 8.
- **Role listing (2026-11-02):** staging CI holds the nine roles of the prompt's table, production CI four; RBAC Administrator with
  its condition on its own resource group only; no Owner, no subscription scope.
- **DORA (staging):** 3 `deploy.yml` runs with a result, 2 successful, change failure rate 1 of 3, time to restore 34 min, lead time
  5 min from merge (12 min from opening PR #10).
- **Post-merge, by the author, in order:** the merge's `deploy.yml` creates `ca-juriscope-stg`; `SKIP_DEPLOY=1 07-staging.sh`
  (redirect URI of the new app, old `ca-juriscope-stg-spc` and its callback removed); `ONLY=browser 07-live-runs.sh` (the code
  flow, ADR-006); `ONLY=load 07-live-runs.sh` (the SLA-02 gate rerun). Results go to `%TEMP%\juriscope-p07`.
- **For phase 8:** read `browser.txt` and the new load results first. If the rerun misses 15 s, no release: the levers are
  ADR-013's options 1 and 2. The `load-test` status is per commit and `release.yml` requires it on the tagged commit with its digest,
  so the load test runs again after the phase 8 merge. `08-production.sh` must give the production CI principal `Juriscope.User`
  and set v2 tokens. Staging is at zero (min 0; the new app starts at zero after its deploy).

## Container Apps environment (author's decision, 2026-11-02, branch `feature/environment`)

- **Limits, read 2026-11-02:** 5 environments per subscription (preflight of the environment alone:
  `MaxNumberOfGlobalEnvironmentsInSubExceeded`, *"cannot have more than 5 Container App Environments"*; 5 exist) and 1 per region
  (`ManagedEnvironmentCount` limit 1, then 2 half an hour later; used: swedencentral 1, spaincentral 3, francecentral 0). `validate` of `main.bicep` against
  production answered `Succeeded` and `what-if` short-circuited the three modules, because the environment sits in a module with
  runtime values; updating an existing environment passes preflight at 5 of 5. So a release that creates a new environment fails only at deployment.
- **Decision (ADR-014):** `cae-juriscope-env` in `rg-juriscope-prod-swc`, `francecentral` (spaincentral would stay at 2 after
  removing Juriscope's, not 0). `infra/modules/environment.bicep` holds the environment and its diagnostic setting; `app.bicep` calls
  it only for production and references it as `existing` in the production resource group for both apps (`dependsOn` the module).
  `appLocation` is `francecentral`. Data stays in `swedencentral`. Express environments, a quota request and sharing a
  staging-named environment were rejected.
- **`deploy.yml`** checks that it can read `cae-juriscope-env` before building. `release.yml` and `load-test.yml` address apps by
  resource group and name and need no change.
- **Cost:** France Central's Consumption meters match Sweden Central's at the API's precision; production at rest about 11.2 € a
  month (`fixedMonthlyEur = '11.2'`), all-in about 0.037 € per question (`cost.md`, ADR-008).
- **`../_scripts/product-legal-juriscope/08-environment.sh`** (author): read-only prechecks (subscription would exceed 5,
  francecentral not free, spaincentral at 0 after removing Juriscope's), then deletes `ca-juriscope-stg` (created in the old
  environment by the phase 7 merge's deploy), `ca-juriscope-stg-spc` and any other app in an old Juriscope environment, then
  `cae-juriscope-stg-spc` and any other old Juriscope environment; validates and deploys `environment.bicep` with concrete values;
  creates the custom role *Juriscope Container Apps Environment Join* (`managedEnvironments/read` and `join/action`, assignable on
  `rg-juriscope-prod-swc`) and assigns it to the staging CI principal on the environment.
- **Author's order:** `08-environment.sh` (after the phase 7 merge's `deploy.yml` has finished); `publish-environment.sh`; merge;
  the merge's `deploy.yml` creates `ca-juriscope-stg` in `cae-juriscope-env`; `SKIP_DEPLOY=1 07-staging.sh` (new callback, old ones
  removed); `ONLY=browser` and `ONLY=load 07-live-runs.sh`. Staging is down from the first step until that deploy. The sign-in
  script runs again after each deploy that recreates or moves an app, because the address changes.
- **For phase 8:** measure every step again from France Central (all dependency calls now cross a region) before trusting SLA-02;
  `08-production.sh` needs no environment work, because production's Bicep redeclares the existing environment unchanged.

## Web parity and release gate (author's decisions, 2026-11-02, branch `feature/web-parity`)

- **`web/` matches the common chat client** in `index.html`, `styles.css` (the common stylesheet as is, plus Juriscope's article,
  version, citation and notice rules after it), the shell in `main.tsx` and the shared dependency versions (`lucide-react` 1.59.0).
  The user block and the user turn show the user icon; under the name, *User* (signed in with the role), *Demo* or *No Juriscope
  role*. The empty state shows the 56 px icon. Progress is one status line with a spinner and the current stage (*Analysing the
  question*, *Searching the Code*, *Reading N articles*, *Drafting*, *Verifying citations*), from the `phase` events; *Analysing
  the question* still appears on send (ADR-013). Kept from phase 5: no `log` role or `aria-busy` on the thread, `inert` on `main`
  while the drawer is open, Escape closes it. Checked with Playwright at 1440x900 and 390x844 (sizes equal; axe clean).
- **Release gate (ADR-015):** `release.yml`'s verify job always requires the staging deploy of the tagged commit, and requires the
  `load-test` status unless every path changed since the previous release that `release.yml` promoted matches `web/**`,
  `docs/**`, any `*.md` or `.github/**`. No such release (v1.0.0 included) requires it. The log prints the paths and the decision.

## Analyst deadline (author's decision, 2026-11-03, branch `fix/analyst-deadline`)

- **Evidence:** the SLA-02 rerun of 2026-11-03 (`load-test.yml` run 41603022081, real-model stage) had 43 asks, 0 failed, and failed
  at p95 17,000 ms. The two slowest asks (29.7 and 21.7 s, warm replicas) spent 24.9 and 15.5 s in *Analyst*'s chat span with 239 and
  179 output tokens; the 15.5 s call's response started at 2.9 s. Staging telemetry over two days: 56 *Analyst* calls, p50 3.4 s,
  p95 11.1 s, input p50 888 tokens, output p50 251; 3 calls over 8 s, all 3 over 11 s, and 4 over 5 s.
- **Decision (ADR-016):** an agent middleware `deadline` on *Analyst* (`app/agents.py`) runs `call_next()` and consumes the stream
  inside `asyncio.timeout(ANALYST_DEADLINE_SECONDS)` (5, the author's choice over the first 8). When the timeout passes it logs the custom event `AnalystRetried` and runs once
  more with no deadline beyond the client's 60-second read timeout. *Counsel* is unchanged. Other errors propagate as before.
- **Verified in the installed wheels:** `agent_framework.agent_middleware` and `AgentContext`. `call_next` can be called again: each
  call runs the agent once more and replaces `context.result`. For a streamed run the middleware itself runs on first iteration, inside
  the workflow's `analyze` step. `ResponseStream.get_final_response()` consumes and finalizes the stream, and a cancelled
  `__anext__` closes the provider stream. A plain `BaseChatClient` wrapper was rejected: `Agent` logs "does not support function
  invoking" on every build.
- **Tests:** `test_slow_analyst_is_cut_and_retried_once` (the deadline patched to 0.1 s; the first attempt 1 s and out of scope, the
  second 0 or 0.3 s). It was shown to fail without the middleware, and its 0.3 s case to fail with a deadline on the second attempt.
  To fit the 700-line test budget, five assertions in `test_workflow.py`, `test_api.py`, `test_corpus.py` and `test_eval.py` were
  written on fewer lines, with the same checks.
- **Expected effect** (ADR-016): a retried ask takes about 5 + 3.4 + 4.8 to 6.2 s ≈ 13.2 to 14.6 s, under 15 s (at 8 s it would be
  16.2 to 17.6 s). 4 of 56 calls (about 7 %) would be cut; cost about 0.00004 € per question. The `ONLY=load` rerun measures it.
- **Author's order:** `publish-analyst-deadline.sh`; merge; `deploy.yml` succeeds on the merge commit; `ONLY=browser`, then
  `ONLY=load 07-live-runs.sh`.

## Phase 8 (2026-11-03, branch `feature/release`)

- **Inputs read:** `browser.txt` (code-flow sign-in and the user's name, both `y`), and `load-test.yml` run 41619345584 on `298ea6a`:
  passed, real model 45 asks, p50 9.3 s, p95 12.0 s, p99 16 s, 0 failed; normal, peak and soak without errors; stress 17 of 3,761
  streams without an outcome at 100 users (no gate). The SLA-02 margin is about 3 s. Staging telemetry stopped at about 10:50 UTC in
  the stress ramp (consistent with the 0.3 GB daily cap, not confirmed), so the real-model window has almost no spans.
- **Fixtures** re-recorded from staging with `python -m ops.record --url <app>` and the author's CLI token for `user_impersonation`
  (11:17 UTC): S1 to S5, all ending in an answer or a refusal; S4's first turn now cites 248 and 131 (limitation), the follow-up 250.
- **Evidence panel** (the build prompt's Demo section, REQ-05 and REQ-07): `web/src/Evidence.tsx` and
  `web/fixtures/evidence/evidence.json` (a subfolder, so the run glob and the axe loop skip it; axe gets `?run=evidence`). It shows
  PR #16's gate comment and the 401 (no session; forged header) and 404 (an id that is not the user's) recorded from staging at
  11:18 UTC, trace ids removed. 403 is unreachable live (assignment required), so the panel says `test_403` proves it.
- **Release checks (read only):** `cae-juriscope-env` exists in francecentral (1 of 2), 4 environments of 5 in the subscription;
  the release adds `ca-juriscope-prod` and creates no environment. `validate` of `main.production.bicepparam` with concrete values
  and of `environment.bicep` alone: `Succeeded`. Production CI holds its four roles; production runtime identity its three.
  Cost Management answered 429 again; Advisor added *zone redundancy for storage* on staging (ADR-011).
- **Author's order:** `08-production.sh`; `publish-release.sh`; merge; `deploy.yml` and `pages.yml` succeed on the merge commit;
  `ONLY=load 07-live-runs.sh` (the `load-test` status on that commit); publish v1.0.0 on that commit; approve; `08-production.sh`
  again.

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
