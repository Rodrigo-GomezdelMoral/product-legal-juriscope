# Operations

The author holds every operational role: deployer, approver, on-call and incident commander. This file says what runs where, how a
change moves, how to undo it and who acts on each alert.

Figures marked *phase 7* or *phase 8* are filled in when those phases measure them live. Until then this file describes the procedure
only.

## Environments

| | Staging | Production |
|---|---|---|
| Resource group | `rg-juriscope-stg-swc` (Sweden Central) | `rg-juriscope-prod-swc` (Sweden Central) |
| Container app | `ca-juriscope-stg-spc` in `cae-juriscope-stg-spc` (Spain Central), 0 to 2 replicas | `ca-juriscope-prod-spc` in `cae-juriscope-prod-spc` (Spain Central), 1 to 4 replicas |
| Data | `cosmos-juriscope-stg-swc`, `stjuriscopestgswc`, `kv-juriscope-stg-swc` | `cosmos-juriscope-prod-swc`, `stjuriscopeprodswc`, `kv-juriscope-prod-swc` |
| Telemetry | `appi-juriscope-stg-swc`, cap 0.3 GB a day | `appi-juriscope-prod-swc`, cap 1 GB a day |
| Search index | `jur-articles-stg` | `jur-articles-prod` |
| Alerts | declared, disabled | enabled |
| Changed by | `deploy.yml`, on every merge to `main` | `release.yml`, on a published release, after approval |

## Promote, roll back, patch

- **To staging:** merge a PR to `main`. `deploy.yml` builds the image once, deploys it by digest with `what-if` first, refreshes the
  corpus and the index (a no-op when the PDF is unchanged), checks `/healthz` on the `canary` label and moves all traffic. It then
  runs the smoke test and uploads the digest as the artifact `image-<sha>`.
- **Load test before any release:** `gh workflow run load-test.yml --ref main`. It sets the commit status `load-test` that
  `release.yml` requires.
- **To production:** `gh release create vX.Y.Z --notes-file <CHANGELOG section>`, then approve the `production` deployment.
  `release.yml` promotes the staging digest of the tagged commit, with 10 % canary for ten minutes and then 100 %, or rolls back.
- **First deployment of an environment:** the Key Vault role and the container app are created in one deployment. If the revision
  fails to read `auth-client-secret` while RBAC propagates, rerun the workflow.
- **Rollback:**
  - staging: `gh workflow run deploy.yml --ref main -f digest=<previous digest>`;
  - production: `gh workflow run release.yml --ref <previous tag>`, with approval.
  - The first release has no previous revision to roll back to.
- **Urgent patch (OE:11):** the same path, pre-approved: `feature/hotfix-<what>`, PR with the required checks, merge, staging, load
  test, `vX.Y.Z+1`.
- **Client secret rotation:**
  1. add a secret to the sign-in app;
  2. update the environment secret `AUTH_CLIENT_SECRET`;
  3. rerun `deploy.yml` (or `release.yml`): Bicep writes the vault secret and the revision reads its latest version;
  4. delete the old secret.

## Alerts

| Alert | Where | Condition | Who acts and how |
|---|---|---|---|
| `alert-juriscope-prod-5xx` | metric, app | more than 5 server errors in 15 minutes | the author: the workbook's health model, then roll back or scale |
| `alert-juriscope-prod-availability` | log, every 15 min | availability of `/api` below 99.7 % over the last hour, with at least 20 requests | the author: triage by flow (*Ask*, *History*, *Model*) |
| `alert-juriscope-prod-latency` | log, every 15 min | p95 of the ask route at or above 6 s over the last hour, with at least 5 questions | the author: *Model* flow and the shared deployment's TPM |
| `budget-juriscope-<env>` | budget, both environments | 50, 80 and 100 % of 10 € (staging) or 25 € (production) | the author: Cost Management by tag; staging to zero, or production `minReplicas 0` |

Each alert goes to its environment's action group `ag-juriscope-<env>-swc`, which e-mails `ALERT_EMAIL_ADDRESS`. Staging declares the
same rules disabled, so that an enabled log rule never bills there.

## Backup and restore

- **Cosmos DB:** continuous backup, 7-day tier, point-in-time restore to a new account. RPO 15 minutes. Learn does not state the
  continuous tier for serverless accounts explicitly; phase 7 confirms it on the deployed account, or falls back to the free
  periodic backup and updates the RPO.
- **Restore drill (phase 7):** restore staging to a new account at a point in time, point a revision at it, read a conversation,
  measure the RTO (target 4 h), delete the restored account.
- **Search index:** rebuilt from the corpus with `python -m ops.index --target <env> --storage-id <id>`.
- **Version store:** part of the image; any earlier image is a full copy.

## Incident procedure (OE:08, SE:12)

1. **Detect:** an alert, or the workbook's health model.
2. **Triage:** by flow. *Ask* is the ask route; *History* is the conversation routes and Cosmos DB; *Model* is Foundry, including 429.
3. **Mitigate:** roll back to the previous release, raise `maxReplicas`, or wait out a shared-quota saturation (the API already
   answers 503 with `Retry-After`).
4. **Communicate:** to the firm's knowledge lead.
5. **Learn:** a post-incident note in `docs/incidents/<date>-<what>.md`.

## Load tests

`load-test.yml` creates a revision of the staging digest with the model double (`MODEL_DOUBLE=true`), labels it `loadtest` with 0 %
of traffic, and runs Locust 2.47.0 headless against that label:

| Scenario | Users | Duration |
|---|---|---|
| normal | 5 | 3 min |
| peak | 20 | 2 min |
| soak | 5 | 10 min |
| stress | +5 a minute | until errors pass 5 %, at most 20 min |

It then runs two minutes at three users on the real model through the stable revision. Search is real in every scenario, so semantic
queries bill. Promotion goes ahead only if the real-model p95 of `ask` is under 8 s (SLA-02) and no scenario fails more than 1 %.

| Date | Scenario | Users | Requests/s | p50 | p95 | p99 | Errors | Replicas |
|---|---|---|---|---|---|---|---|---|
| *phase 7* | | | | | | | | |

## DORA

Read from the Actions runs with `gh run list --workflow deploy.yml` and `--workflow release.yml`, with dates:
- deployment frequency;
- lead time from merge to staging and from tag to production;
- change failure rate (failed or rolled-back releases);
- time to restore.

*Phase 8.*

## Switching on and off

- Staging scales to zero by itself.
- Production's warm replica and its two log alert rules are the only standing cost (about 15.5 € a month, `docs/cost.md`).
- Prompt 06 sets production `minReplicas` to 0 and disables the alert rules without deleting anything.

## Cost per environment

Estimated in `docs/cost.md`; measured in Cost Management by the `project` and `environment` tags at the end of phase 7.
