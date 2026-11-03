# ADR-015 · Release without a load test when only the web, docs or workflows changed

**Status:** accepted (author's decision) · **Date:** 2026-11-02

## Context

`release.yml` promotes the staging digest of the tagged commit only if two things hold: `deploy.yml` deployed that commit to
staging on merge, and the commit status `load-test` is `success` for the same digest (ADR-012). The load test measures the API's
latency against SLA-02 (ADR-013): it runs the model-double scenarios and the real-model scenario against a staging revision, about
35 minutes of a shared model deployment's quota.

A release that only changes the web client, the documentation or the workflows changes nothing the load test measures. The web is
static files the API serves; docs and Markdown are not in the image; workflows run on the runner. Running the load test for such a
release spends the time and the shared quota and proves nothing new about the API.

## Options

1. **Always require the load test.** Safe and simple, but every web or docs release waits about 40 minutes and loads the shared
   deployment for no new evidence.
2. **A manual override** (a workflow input to skip the check). Rejected: it depends on judgement at release time and leaves no
   rule a reader can check.
3. **Skip it by the paths changed since the previous release** (chosen).

## Decision

- The verify job of `release.yml` always requires a successful `deploy.yml` run for the tagged commit, with its digest artifact.
- It finds the previous published release (not a draft, published before this one) that `release.yml` promoted, that is whose run
  succeeded, and lists every path changed between that tag and the tagged commit (`git diff --name-only --no-renames`, so a
  rename counts both paths). The checkout fetches the full history and the tags.
- The load test is **not** required only when every changed path matches `web/**`, `docs/**`, any `*.md` or `.github/**`. Any
  other path, or no previous release, requires it as before. The first release, v1.0.0, therefore still needs the load test.
- The job log prints the changed paths and the decision.

## Consequences

- A web, docs or workflow release goes to production after the staging deploy, without waiting for the load test. The canary with
  its smoke test and its requests and 5xx check by revision (ADR-012, revised in 1.0.1) still guards production.
- A release whose `release.yml` run did not succeed (it failed in verify without its load test, or was rolled back) is never the
  baseline, so an API change it carried cannot reach production later behind a web-only change.
- A workflow change (for example to `load-test.yml` or `deploy.yml`) does not trigger the load test by itself; its effect shows on
  the next run of that workflow.
