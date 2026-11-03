# Threat model

A light STRIDE pass over Juriscope as deployed: a browser, one container app (FastAPI and the web client) in France Central behind
Container Apps authentication, the shared Foundry models and AI Search, and Cosmos DB, Storage, Key Vault and Application
Insights in Sweden Central. Each mitigation names the test or live check that proves it. **Implemented** means in code or Bicep;
**proven** means the named check has passed. The live checks ran on staging on 2026-11-01 (phase 7); phase 8 repeats the
release ones in production.

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
| **Spoofing** | Easy Auth with Entra ID, code flow, assignment required; the API trusts only `X-MS-CLIENT-PRINCIPAL`, which the platform sets (ADR-006) | `test_api.py::test_401`; live: 401 without a session, and a forged `X-MS-CLIENT-PRINCIPAL` sent from outside is not honoured | test passes; proven live (staging, 2026-11-01): 401 without a session and with an invalid bearer; the forged header got 401 alone and was replaced by Easy Auth beside a valid token |
| **Tampering** | ruleset `protect-main` with required checks `ci` and `eval`; images deployed by digest; OIDC without secrets; dependencies pinned with `==` and base images by digest; actions pinned to a major version and updated by Dependabot | ruleset listing; the release log shows the digest staging received; `tests/test_budget.py::test_supply_chain_is_pinned` | test passes; staging runs digest-only revisions (`deploy.yml`); the release log in phase 8 |
| **Repudiation** | requests and KPI events carry `user_hash` (SHA-256 of the object id, 16 hex) and the trace id | KQL over `requests` and `customEvents` | proven (staging, 2026-11-01): `QuestionAsked` 6, `AnswerDelivered` 6, `AnswerAccepted` 2, `FeedbackGiven` 1, all with `user_hash` and `turn_id` and no text; a 404's `trace_id` is its request's `operation_Id` |
| **Information disclosure** | Cosmos DB partition key is the user's object id; no question or answer text in telemetry; `store: False` on model calls; local and shared-key auth disabled on Cosmos DB, Storage and Application Insights; Key Vault by RBAC; 90-day TTL | `test_api.py::test_404_other_user`; the telemetry test asserting no question text; Bicep `disableLocalAuth`, `allowSharedKeyAccess: false`, `defaultTtl` | tests pass; deployed to staging: both containers `defaultTtl` 7,776,000, local auth off |
| **Denial of service and cost** | max replicas (2 staging, 4 production); TPM caps on the shared deployments; `max_tokens` per agent; budgets with alerts at 50, 80 and 100 %; Application Insights daily caps (0.3 and 1 GB); a model 429 answered with 503 and `Retry-After` | Locust stress results in `OPERATIONS.md`; `test_api.py` 429 → 503 | test passes; stress proven (staging, 2026-11-01): 5 to 100 users over 20 minutes, 4,159 asks, 0 failed, at most 2 replicas, CPU saturated from about 70 users, no 429 from any dependency |
| **Elevation of privilege** | the `Juriscope.User` role claim checked in the app; RBAC Administrator for CI limited by condition to four roles and one resource group; no Owner and no subscription scope for any workload identity | `test_api.py::test_403`; the role listing | test passes; listing (2026-11-02): no Owner and no subscription scope for either CI principal; RBAC Administrator with its condition on its own resource group only |
| **Prompt injection** | Prompt Shields (jailbreak) in the shared guardrail; retrieval decided by code; claims whose citations were not retrieved are dropped; passages that are not the legal question are removed before *Counsel* sees it; canary phrase in the adversarial set | the adversarial evaluation (canary 0 of 15 on 2026-10-31) | proven on `jur-articles-stg`: canary 0 of 15 in the full suite (2026-11-01) |

## Residual risks

- **Global Standard inference** may process a question outside the EU (ADR-009).
- **One search replica** without an SLA sits under SLA-01 (ADR-007).
- **Search roles at service scope** (2026-11-03): both runtime identities hold Search Index Data Reader on the whole shared search
  service, so staging's identity can read the production index and other workloads' indexes, and both CI principals hold Search
  Service Contributor there, which indexers and skillsets need. Planned: Search Index Data Reader scoped to each environment's
  own index, through an author script, in a later release.
- **Public workflow logs** printed non-secret identifiers (the sign-in app's client id, the shared endpoints, the registry host,
  resource GUIDs from `what-if`) until release 1.0.1. Since then they are secrets, which GitHub masks, and `what-if` GUIDs are
  replaced. Earlier run logs are kept as the DORA evidence.
- **The client secret** is a long-lived credential. It lives only in Key Vault and in a GitHub environment secret, and
  `OPERATIONS.md` gives the rotation steps (ADR-006).
- **The static web client is served without a session.** It holds no data: every data route requires the principal and the role.
- **Public network access** is on for Cosmos DB, Storage and Key Vault, which accept only Entra ID tokens. Private endpoints are
  rejected in ADR-011.
