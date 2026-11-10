# Architecture

```mermaid
graph LR
    U["Lawyer · browser"] -->|Entra sign-in · Easy Auth| CA["ca-juriscope-stg or -prod in cae-juriscope-env · FastAPI + web · France Central"]
    CA --> WF["Juriscope workflow · WorkflowBuilder"]
    WF --> AN["analyze · Analyst · gpt-5-mini"]
    WF --> RT["retrieve · code"]
    WF --> DR["draft · Counsel · gpt-5-mini"]
    WF --> VF["verify · code"]
    RT --> SRCH[("srch-aiplatform-shared · Spain Central · jur-articles-env")]
    RT --> STORE[("data/boe/articles.json · versions, in the image")]
    CA --> COSMOS[("cosmos-juriscope-env-swc · history and conversations")]
    AN & DR --> FDRY["proj-aiplatform-shared · Sweden Central"]
    BLOB[("stjuriscopeenvswc · corpus · PDF in parts")] --> IDXR["indexer · text extraction · split · embeddings"] --> SRCH
    CA --> KV[("kv-juriscope-env-swc · client secret")]
    CA --> APPI["appi-juriscope-env-swc"] --> LAW[("log-aiplatform-shared-swc")]
```

## Regions

- **France Central:** one Container Apps environment, `cae-juriscope-env`, in `rg-juriscope-prod-swc`, shared by `ca-juriscope-stg`
  (in `rg-juriscope-stg-swc`) and `ca-juriscope-prod`. The subscription allows 5 environments and each region 1 or 2; France Central was
  the free one (ADR-014, author's decision of 2026-11-02).
- **Spain Central:** the shared AI Search service.
- **Sweden Central:** everything else of each environment (Cosmos DB, Storage, Key Vault, Application Insights, the runtime
  identity) and the shared Foundry account, registry and workspace.

Every dependency call leaves France Central: search to Spain Central, model, Cosmos DB, Key Vault and telemetry calls to Sweden
Central, a few KB per question. From France Central, the SLA-02 load test of 2026-11-09 on the released image (v1.0.2) measured an
exact real-model p95 of 11.3 s at the client (100 answers, with ADR-016's deadline on *Analyst*). Nothing is stored at rest in France Central,
and in Spain Central only the public text of the Code in the search index (ADR-009).

## Request path

1. The browser loads the web client from the container app. The client calls `/api/me`; without a session it gets a 401 and goes to
   `/.auth/login/aad`.
2. Easy Auth completes the Entra code flow and sets a session cookie. From then on it injects `X-MS-CLIENT-PRINCIPAL` into every
   request. `app/auth.py` requires the `Juriscope.User` role.
3. `POST /api/conversations/{id}/messages` runs the workflow (ADR-001) and streams `phase` events, then one `answer` or `refusal`,
   over SSE (ADR-004). History and the conversation record are written to Cosmos DB under the user's partition (ADR-002).
4. Telemetry goes to Application Insights with the runtime identity; KPI events carry `user_hash`, never text.

## Deployment path

`ci.yml` and `eval.yml` gate every PR. A merge to `main` builds one image on the runner and deploys it to staging by digest
(`deploy.yml`). After the load test passes, a GitHub Release promotes that digest to production with a 10 % canary
(`release.yml`, ADR-012). The infrastructure is `infra/main.bicep` with one parameter file per environment. Every deployment runs
`what-if` first.

| Module | Resources |
|---|---|
| `infra/main.bicep` | references to the runtime identity, the shared search service and the workspace; the environment's settings |
| `modules/data.bicep` | Cosmos DB (serverless, continuous backup 7 days, two containers with a 90-day TTL, data-plane role), Storage (`corpus`, soft delete), Key Vault (RBAC, the client secret) and their roles |
| `modules/monitor.bicep` | Application Insights (workspace-based, local auth off, daily cap), the workbook, the budget, the action group, two log alerts |
| `modules/app.bicep` | the app (multiple revisions, probes, scale rule, Key Vault secret reference) in the shared environment, Easy Auth, the 5xx metric alert |
| `modules/environment.bicep` | `cae-juriscope-env` and its diagnostic setting to the shared workspace; production declares it, staging references it (ADR-014) |
| `modules/roles.bicep` | built-in role names, shared by the modules |
