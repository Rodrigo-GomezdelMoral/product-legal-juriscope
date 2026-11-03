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
  of traffic for twelve minutes, after a smoke test on the label; the workflow reads that revision's requests and 5xx from the
  Container Apps `Requests` metric, filtered on its revision name; then 100 %, or traffic goes back and the run fails. Staging goes
  straight to 100 % once the canary label passes `/healthz`.
- **Rollback:** an explicit promotion of an earlier release: `deploy.yml` with the previous digest for staging, then `release.yml`
  dispatched with the previous tag as input, with approval; the fast path re-activates the previous revision (OPERATIONS.md).

**Revised 2026-11-03 (release 1.0.1), after the validation:**
- Until 1.0.1 the canary step read Application Insights requests whose `cloud_RoleInstance` starts with the revision name. That
  field is a per-process id, so the query always returned 0 requests and the check always passed. The `Requests` metric has
  `revisionName` and `statusCodeCategory` dimensions; `ResponseTime` has no revision dimension, so the p95 of one revision is not
  measured until the app sets `service.instance.id` from the replica name, an `app/` change planned for the next release with a
  load test. At about 350 questions a month, 10 % of twelve minutes rarely holds a request, so the summary says when the 5xx rule
  did not apply; the label smoke test always runs.
- A dispatch reused the revision suffix `v<major>-<minor>-<patch>` of a revision that already exists, which Container Apps rejects
  (Learn on revision-scope changes and a Microsoft Q&A answer; not tried live).
  A dispatch now appends `-r<run number>`, and takes the tag to deploy as an input, because a dispatch on an old tag would run
  that tag's own, older workflow.

## Consequences

- The first release has no previous revision: it gets 100 % at once, after the health check, and has nothing to roll back to.
- Base images are pinned by digest in the `Dockerfile`; Dependabot (`docker`) proposes updates, which pass CI and the gate like any
  change.
- Artifacts are kept 90 days, so a release must come within 90 days of its merge, or `deploy.yml` is rerun on that commit.
