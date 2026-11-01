# Threat model

A light STRIDE pass over Juriscope as deployed: a browser, one container app (FastAPI and the web client) in Spain Central behind
Container Apps authentication, the shared Foundry models and AI Search, and Cosmos DB, Storage, Key Vault and Application
Insights in Sweden Central. Each mitigation names the test or live check that proves it. **Implemented** means in code or Bicep;
**proven** means the named check has passed. The live checks belong to phase 7 (staging) and phase 8 (production).

## Assets

- the lawyers' questions and answers, which may hold special-category data (GDPR article 10) under professional secrecy;
- the sign-in app's client secret;
- the integrity of the answers: citations to articles in the version that applies;
- the shared model quota and the monthly budget.

## Trust boundaries

1. Browser → container app ingress (HTTPS, Easy Auth).
2. Container app → Azure services, with the runtime identity `id-juriscope-<env>-swc` and no keys.
3. GitHub Actions → Azure, with OIDC federated credentials per environment and no secrets.
4. Model output → the answer: the model's claims are checked by code before anyone sees them.

## STRIDE

| Threat | Mitigation | Proof | State |
|---|---|---|---|
| **Spoofing** | Easy Auth with Entra ID, code flow, assignment required; the API trusts only `X-MS-CLIENT-PRINCIPAL`, which the platform sets (ADR-006) | `test_api.py::test_401`; live: 401 without a session, and a forged `X-MS-CLIENT-PRINCIPAL` sent from outside is not honoured | test passes; live in phase 7 |
| **Tampering** | ruleset `protect-main` with required checks `ci` and `eval`; images deployed by digest; OIDC without secrets; pinned dependencies, actions and base images | ruleset listing; the release log shows the digest staging received; `tests/test_budget.py::test_supply_chain_is_pinned` | test passes; release in phase 8 |
| **Repudiation** | requests and KPI events carry `user_hash` (SHA-256 of the object id, 16 hex) and the trace id | KQL over `requests` and `customEvents` | live in phase 7 |
| **Information disclosure** | Cosmos DB partition key is the user's object id; no question or answer text in telemetry; `store: False` on model calls; local and shared-key auth disabled on Cosmos DB, Storage and Application Insights; Key Vault by RBAC; 90-day TTL | `test_api.py::test_404_other_user`; the telemetry test asserting no question text; Bicep `disableLocalAuth`, `allowSharedKeyAccess: false`, `defaultTtl` | tests pass; Bicep in `what-if` |
| **Denial of service and cost** | max replicas (2 staging, 4 production); TPM caps on the shared deployments; `max_tokens` per agent; budgets with alerts at 50, 80 and 100 %; Application Insights daily caps (0.3 and 1 GB); a model 429 answered with 503 and `Retry-After` | Locust stress results in `OPERATIONS.md`; `test_api.py` 429 → 503 | test passes; stress in phase 7 |
| **Elevation of privilege** | the `Juriscope.User` role claim checked in the app; RBAC Administrator for CI limited by condition to four roles and one resource group; no Owner and no subscription scope for any workload identity | `test_api.py::test_403`; the role listing | test passes; listing in phase 7 |
| **Prompt injection** | Prompt Shields (jailbreak) in the shared guardrail; retrieval decided by code; claims whose citations were not retrieved are dropped; passages that are not the legal question are removed before *Counsel* sees it; canary phrase in the adversarial set | the adversarial evaluation (canary 0 of 15 on 2026-10-31) | evaluated locally; repeated on `jur-articles-stg` in phase 7 |

## Residual risks

- **Global Standard inference** may process a question outside the EU (ADR-009).
- **One search replica** without an SLA sits under SLA-01 (ADR-007).
- **The client secret** is a long-lived credential. It lives only in Key Vault and in a GitHub environment secret, and
  `OPERATIONS.md` gives the rotation steps (ADR-006).
- **The static web client is served without a session.** It holds no data: every data route requires the principal and the role.
- **Public network access** is on for Cosmos DB, Storage and Key Vault, which accept only Entra ID tokens. Private endpoints are
  rejected in ADR-011.
