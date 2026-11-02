# ADR-014 · One Container Apps environment for staging and production

**Status:** accepted (author's decision) · **Date:** 2026-11-02

## Context

Phase 6 planned two Container Apps environments, `cae-juriscope-stg-spc` and `cae-juriscope-prod-spc`, because a Consumption-only
environment is free at rest. Two limits, checked on 2026-11-02, make a second environment per product unaffordable in this
subscription:

- **5 environments per subscription.** The preflight check of the environment resource alone, with concrete values, answers
  `MaxNumberOfGlobalEnvironmentsInSubExceeded`: *"cannot have more than 5 Container App Environments"*. The subscription already
  holds 5, Juriscope staging among them. The limit is not listed on Learn's
  quotas page and does not appear in the usages API.
- **A per-region limit.** The usages API (`ManagedEnvironmentCount`, *subscription and region* on Learn's quotas page) gives a
  limit of 1 at the first read on 2026-11-02 and of 2 half an hour later (Sweden Central 1, Spain Central 3, France Central 0 used).
  The value moves; the 5-environment limit above is the binding one.
- **Neither is visible to `validate` or `what-if` of `main.bicep`.** The environment is declared inside the `app` module, which
  receives runtime values (the action group's id, the Key Vault secret URI), so preflight never evaluates it and `what-if`
  short-circuits the nested deployments. On 2026-11-02 `validate` of `main.bicep` against production answered `Succeeded` while the
  same environment validated alone failed on the 5-environment limit, so a release that creates an environment fails only at
  deployment. Updating an
  environment that already exists passes preflight at 5 of 5.

## Options

1. **Ask for more quota.** Rejected: the per-region quota request goes through the Quota Management System and may be routed to
   Support with no date, and the 5-per-subscription limit has no documented request path. The release would wait on it.
2. **Production joins the staging environment as it is (`cae-juriscope-stg-spc`).** Rejected: a production app in an environment
   named and tagged for staging, deployed by staging's Bicep, misleads every reader and every cost query.
3. **Express environments**, 200 per region. Rejected: Learn lists no Easy Auth (ADR-006), no Key Vault secret references, no custom
   KEDA scalers, a single revision with no traffic splitting and no deployment labels, so neither the canary (ADR-012) nor the
   load-test revision behind its label would work.
4. **One environment per product, `cae-juriscope-env`** (chosen).

## Decision

- **`cae-juriscope-env`**, without `stg`, `prod` or a region code, in the existing `rg-juriscope-prod-swc`, in **France Central**
  (0 used). The rule of 2026-11-02: Spain Central only if removing Juriscope's environment there left it at 0, which would mean
  every other environment there had moved; it leaves 2. `08-environment.sh` checks it again and stops if it has changed.
- **Production declares it** (`infra/modules/environment.bicep`, called from `app.bicep` when `env` is `production`), with the
  diagnostic setting that sends its logs to the shared workspace. **Staging references it** as `existing` in the production resource
  group. `ca-juriscope-stg` stays in `rg-juriscope-stg-swc`, `ca-juriscope-prod` in `rg-juriscope-prod-swc`, both in France Central.
- **The author creates it first** with `08-environment.sh`, from the same Bicep file: the old Juriscope apps and environment are
  deleted before anything is created, because of the subscription limit; the environment alone is validated with concrete values,
  then deployed. The staging CI principal gets a custom role with only `Microsoft.App/managedEnvironments/read` and
  `Microsoft.App/managedEnvironments/join/action` on the environment, which is what creating an app in an environment of another
  resource group needs. `deploy.yml` checks that it can read the environment before building.
- **Data stays in Sweden Central:** Cosmos DB, Storage, Key Vault, Application Insights, the identities and the resource groups do
  not move. The Container Apps keep nothing at rest (ADR-009).
- **After each deploy that recreates or moves an app,** `07-staging.sh` runs again with `SKIP_DEPLOY=1`, because the app's address,
  and so the sign-in callback, changes with the environment.

## Consequences

- **Shared between staging and production:** the environment's configuration, that is its log destination (the shared workspace
  through one diagnostic setting), its network (public, no virtual network), its platform updates and maintenance, and its
  Consumption cores quota (100 per environment; staging at most 2 replicas plus the load revision's 2, production 4, at 0.5 vCPU each).
  A change to the environment, or a platform incident in it, reaches both apps at once.
- **Still separate:** the apps, their revisions and scale rules, the runtime and CI identities, the data, Easy Auth and its sign-in
  apps, the resource groups and budgets. Logs carry the app name, so queries keep filtering by app.
- **Latency:** the app now runs in France Central, away from the search service (Spain Central) and the models and data (Sweden
  Central): every dependency call crosses a region. Phase 8 measures the steps again in production; if SLA-02 (ADR-013) slips, the
  levers are ADR-013's options and moving the environment to Sweden Central or Spain Central when either frees up.
- **Cost:** the environment is free at rest. France Central's Consumption meters match Sweden Central's at the Retail Prices API's
  precision (vCPU active 0.000022 € a second, idle 0.000003 €, 2026-11-02), below Spain Central's, so production at rest falls
  from about 15.5 to 11.2 € a month and the all-in cost per question to about 0.037 € (`docs/cost.md`, ADR-008).
