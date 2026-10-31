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
  `../_scripts/product-legal-juriscope/<nn>-<what>.sh`; write the script and stop. Written: `01-codeql.sh` (phase 1). Planned:
  `03-eval-variables.sh` (phase 3), `07-staging.sh` (phase 7), `08-production.sh` (phase 8).
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
- **Pending:** the search service `srch-aiplatform-shared-neu` does not exist yet, so every search role (CI, runtime, the author's
  and the search identity's on Foundry) is pending. Phase 2 starts by checking that it is `running`; if not, it stops and reports.
- **Quotas:** Cosmos DB region access in `swedencentral` allowed, no accounts yet; no Key Vaults, active or soft-deleted; storage
  accounts 0 of 250 in the region; the global names `kv-juriscope-*`, `stjuriscope*` and `cosmos-juriscope-*` are available.
  **Container Apps managed environments: 15** in `swedencentral`, 0 used. Each product has one environment per stage, all in
  `swedencentral`: `cae-juriscope-stg-swc` and `cae-juriscope-prod-swc`. Nothing is shared and no other region is used.
  Consumption cores are a per-environment quota, readable only once an environment exists.

## Decisions taken in phase 0

- **Dependencies.** `requirements.txt` holds what the image runs (`app/`). `requirements-dev.txt` adds what runs on the runner or the
  laptop: `ops/` (Blob upload, BOE client, PDF split), `eval/` (`azure-ai-evaluation`, YAML thresholds), `load/` (Locust), tests and
  tooling. This keeps `azure-ai-evaluation` and Locust out of the image. The whole set was installed together on Python 3.12 and
  `pip check` passed.
- **Dependabot** watches `pip` (the `agent-framework-*` packages grouped, so the core and its integrations, which each require a
  minimum `agent-framework-core`, move together) and `github-actions`. Phase 5 adds `npm` and phase 6 adds `docker`, in the same
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
