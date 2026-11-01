# ADR-012 · Build once on the runner, promote the digest, canary in production

**Status:** accepted · **Date:** 2026-11-01

## Context

What reaches production must be exactly what passed staging, the evaluation gate and the load test. The registry is Basic and shared.

## Options

1. **Build in the registry with ACR Tasks:** no Docker on the runner, but it would need another role on the shared registry.
2. **Build on the runner** with Buildx, push with `az acr login` under the staging CI identity (AcrPush) (chosen).
3. **Rebuild for production from the tag:** a second build can differ (base image, dependency resolution); rejected.

## Decision

Option 2.

- **Build once:** one image per merge to `main`, tagged `<yyyymmdd>-main-<sha7>`.
- **Promote by digest:** `deploy.yml` deploys it to staging by digest and uploads the digest as the artifact `image-<sha>`.
  - `release.yml` finds the successful `deploy.yml` run for the tag's commit and downloads that artifact.
  - It also requires the `load-test` commit status to be `success` for that same digest, then deploys it to production.
  - The production identity has AcrPull only, through its runtime identity.
- **Canary:** each production revision is named after the release (`v1-0-0`) and starts behind the `canary` label. It then gets 10 %
  of traffic for ten minutes, after a smoke test on the label, while the workflow reads its 5xx rate and p95 from Application
  Insights; then 100 %, or traffic goes back and the run fails. Staging goes straight to 100 % once the canary label passes `/healthz`.
- **Rollback:** an explicit promotion of an earlier release: `deploy.yml` with the previous digest for staging, then `release.yml` on
  the previous tag, with approval.

## Consequences

- The first release has no previous revision: it gets 100 % at once, after the health check, and has nothing to roll back to.
- Base images are pinned by digest in the `Dockerfile`; Dependabot (`docker`) proposes updates, which pass CI and the gate like any
  change.
- Artifacts are kept 90 days, so a release must come within 90 days of its merge, or `deploy.yml` is rerun on that commit.
