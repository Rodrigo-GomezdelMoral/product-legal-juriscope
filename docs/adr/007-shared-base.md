# ADR-007 · What is shared with the platform and what each environment owns

**Status:** accepted · **Date:** 2026-11-01

## Context

Four products (P05 to P08) run on one subscription with a shared base in `rg-aiplatform-shared-swc`: the Foundry account and its
model deployments, an AI Search service, a container registry and a Log Analytics workspace. The production budget is 25 € a month.
Customer data is covered by professional secrecy (GDPR article 10).

## Decision

**Shared, by logical isolation:**

| Resource | Why shared | Isolation |
|---|---|---|
| Foundry `gpt-5-mini` and `text-embedding-3-small` | per-token billing, TPM-capped deployments | `store: False`; nothing persisted by the model service |
| AI Search `srch-aiplatform-shared` (Basic, Spain Central) | Basic bills about 64.88 € a month whether used or not | one index per environment (`jur-articles-stg`, `-prod`, `-local`) holding only the public Code; the runtime identity has Search Index Data Reader |
| Registry `craiplatformshared` | Basic bills daily | images by digest; staging pushes, both identities pull |
| Log Analytics `log-aiplatform-shared-swc` | first 5 GB a month free per billing account | each environment has its own workspace-based Application Insights; `environment` is a tag and a dimension |

**Owned by each environment, never shared:**
- the resource group, budget and action group;
- the runtime identity `id-juriscope-<env>-swc` and the CI identity;
- Cosmos DB (the conversations), Storage (the corpus parts), Key Vault (the client secret), Application Insights;
- the Container Apps environment and app.

**Identity:**
- The runtime identities are created by `01-azure.sh`, not by Bicep, because they need roles on the shared base (AcrPull, Foundry
  User, Search Index Data Reader). The CI identities' RBAC Administrator role is limited to the resource group and to the four roles
  this Bicep assigns.
- The Bicep reads only the shared search service (its identity, for the corpus role) and the workspace (its id). The registry
  login server and the Foundry and search endpoints come from repository variables, so the production CI identity needs no read
  role on the registry.

**Availability:** the search service has one replica and no financially backed SLA. SLA-01 (99.5 %) is measured, not inherited, and
a second replica (about 64.88 € a month) is rejected against a 25 € budget.

## Consequences

- One Spain Central search service holds at most 15 indexes for all products; Juriscope uses three.
- A shared model deployment can be saturated by another product (all four share 100K TPM). The API turns that into a 503 with
  `Retry-After`, and the health model's *Model* flow shows it.
- Deleting a product never touches the shared base; prompt 06 removes only the environment resource groups.
