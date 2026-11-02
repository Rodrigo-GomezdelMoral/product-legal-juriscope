# Operations

The author holds every operational role: deployer, approver, on-call and incident commander. This file says what runs where, how a
change moves, how to undo it and who acts on each alert.

Staging figures were measured in phase 7 (2026-11-01, times in UTC); figures marked *phase 8* come with the first release.

## Environments

| | Staging | Production |
|---|---|---|
| Resource group | `rg-juriscope-stg-swc` (Sweden Central) | `rg-juriscope-prod-swc` (Sweden Central) |
| Container app | `ca-juriscope-stg` in `cae-juriscope-env` (France Central), 0 to 2 replicas | `ca-juriscope-prod` in `cae-juriscope-env`, 1 to 4 replicas |
| Container Apps environment | shared: `cae-juriscope-env` in `rg-juriscope-prod-swc`; staging's CI joins it with a custom role (ADR-014) | declared by production's Bicep |
| Data | `cosmos-juriscope-stg-swc`, `stjuriscopestgswc`, `kv-juriscope-stg-swc` | `cosmos-juriscope-prod-swc`, `stjuriscopeprodswc`, `kv-juriscope-prod-swc` |
| Telemetry | `appi-juriscope-stg-swc`, cap 0.3 GB a day | `appi-juriscope-prod-swc`, cap 1 GB a day |
| Search index | `jur-articles-stg` | `jur-articles-prod` |
| Alerts | declared, disabled | enabled |
| Changed by | `deploy.yml`, on every merge to `main` | `release.yml`, on a published release, after approval |

## Promote, roll back, patch

- **Switch:** `deploy.yml` runs only while the **repository** variable `DEPLOY_ENABLED` is `true`. It cannot be an environment
  variable: a job-level `if` is evaluated before the job's environment exists. `release.yml` does not read it.
- **To staging:** merge a PR to `main`. `deploy.yml` builds the image once, deploys it by digest with `what-if` first, refreshes the
  corpus and the index (a no-op when the PDF is unchanged), checks `/healthz` on the `canary` label and moves all traffic. It then
  runs the smoke test and uploads the digest as the artifact `image-<sha>`.
- **Load test before any release:** `gh workflow run load-test.yml --ref main`. It sets the commit status `load-test`, naming the
  digest it tested, that `release.yml` requires.
- **To production:** `gh release create vX.Y.Z --notes-file <CHANGELOG section>`, then approve the `production` deployment.
  `release.yml` promotes the staging digest of the tagged commit, with 10 % canary for ten minutes and then 100 %, or rolls back.
- **First deployment of an environment:** the Key Vault role and the container app are created in one deployment. If the revision
  fails to read `auth-client-secret` while RBAC propagates, rerun the workflow. Staging avoided it with a temporary Key Vault
  Secrets User on the resource group (`07-staging.sh`), removed after the first revision; later revisions resolve the secret with
  the vault-scoped role alone.
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
| `alert-juriscope-prod-latency` | log, every 15 min | p95 of the ask route at or above 13 s (the latency SLO) over the last hour, with at least 5 questions | the author: *Model* flow and the shared deployment's TPM |
| `budget-juriscope-<env>` | budget, both environments | 50, 80 and 100 % of 10 € (staging) or 25 € (production) | the author: Cost Management by tag; staging to zero, or production `minReplicas 0` |

Each alert goes to its environment's action group `ag-juriscope-<env>-swc`, which e-mails `ALERT_EMAIL_ADDRESS`. Staging declares the
same rules disabled, so that an enabled log rule never bills there (checked deployed on 2026-11-01: the three rules exist,
disabled). Application Insights adds a *Failure Anomalies* smart detector by itself; it is free and not in Bicep.

## Backup and restore

- **Cosmos DB:** continuous backup, 7-day tier, point-in-time restore to a new account. RPO 15 minutes. Learn does not state the
  continuous tier for serverless accounts explicitly; the deployed staging account shows `Continuous7Days` on serverless.
- **Restore drill (staging, 2026-11-01):**
  1. `az cosmosdb restore` of `cosmos-juriscope-stg-swc` to the new account `cosmos-juriscope-stg-drill` at 12:24:14, decided
     at 12:31:30;
  2. `Succeeded` at 12:42:36 (11 min 6 s);
  3. local auth enabled on the restored account only, and a read-only key read 3 conversations and 4 history messages at 12:43:47:
     **12 min 17 s from the decision to readable data, against the 4 h RTO**;
  4. the restored state matched the live one about 25 s before the requested point (a conversation started at 12:23:51 was
     missing), inside the 15 min RPO;
  5. the restored account was deleted. Restores bill per GB restored, so a few KB cost nothing measurable.
  - **Not rehearsed:** pointing the app at a restored account. That means changing the Cosmos DB account name in
    `infra/modules/data.bicep` (or restoring under the original name after deleting it) and redeploying; budget about 30 minutes
    more for it, still far inside the RTO.
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

It then waits for `/healthz` 200 on the stable revision and runs five minutes at three users on the real model through it. Search is
real in every scenario, so semantic queries bill. Promotion goes ahead only if the real-model p95 of `ask` is under 15 s (SLA-02,
restated in ADR-013) and no scenario fails more than 1 %. Replicas, CPU and memory maxima come from Azure Monitor.

| Date | Scenario | Users | Requests/s | p50 | p95 | p99 | Errors | Replicas |
|---|---|---|---|---|---|---|---|---|
| 2026-11-01 | normal, model double | 5 | 0.45 | 1.0 s | 5.1 s | 5.2 s | 0 of 79 | 1 |
| 2026-11-01 | peak, model double | 20 | 1.69 | 1.2 s | 7.7 s | 7.8 s | 0 of 203 | 1 |
| 2026-11-01 | soak, model double | 5 | 0.44 | 0.97 s | 1.4 s | 1.7 s | 0 of 267 | 2 |
| 2026-11-01 | stress, model double | 5 to 100 | 3.47 | 2.3 s | 10 s | 16 s | 0 of 4,159 | 2 (the maximum) |
| 2026-11-01 | real model, cold stable revision | 3 | 0.13 | 9.7 s | 37 s | 37 s | 0 of 14 | 0 → 1 |

Rates and percentiles are for the ask route at the client (Locust 2.47.0, run 41331036489, digest of `c074a7e`). **The run failed
the SLA-02 gate** as it stood then (p95 < 8 s): the stable revision had idled at zero replicas through the 35 minutes of the
model-double scenarios, and the first three real asks waited 25.5 s for a replica. Server-side, the 15 real asks took 7.2 to
13.7 s (median 9.5 s, p95 13.7 s). The stress ramp never reached 5 % errors: CPU saturated at 0.51 vCPU from about 70 users and
probes timed out in the last two minutes, without a failed ask. Working set peaked at 0.53 GiB, so the replica stays at 0.5 vCPU
and 1 GiB (ADR-008). No dependency returned 429. **The gate is rerun with the warm-up and the longer real-model scenario after the
phase 7 merge, before any release.**

## DORA

Read from the Actions runs with `gh run list --workflow deploy.yml` and `--workflow release.yml`, with dates:
- deployment frequency;
- lead time from merge to staging and from tag to production;
- change failure rate (failed or rolled-back releases);
- time to restore.

| Window | Deployment frequency | Lead time | Change failure rate | Time to restore |
|---|---|---|---|---|
| Staging, 2026-11-01 | 3 `deploy.yml` runs with a result, 2 successful (one commit, `c074a7e`) | PR #10: 5 min from merge (12:06) to staging (12:11), 12 min from opening | 1 of 3 (11:37, the Layout skill rejected in Spain Central) | 34 min, restored by PR #10 |
| Production | *phase 8* | | | |

## Switching on and off

- Staging scales to zero by itself.
- **The environment is created by the author**, once, with `08-environment.sh` (ADR-014): it deletes the old Juriscope apps and
  environments, validates and deploys `infra/modules/environment.bicep`, and gives the staging CI principal read and join on it.
  `deploy.yml` stops with a clear error if it cannot read it. A change to the environment reaches both apps.
- **After every deploy that recreates or moves an app,** run `SKIP_DEPLOY=1 07-staging.sh` again: the app's address, and so the
  sign-in callback, changes.
- Production's warm replica and its two log alert rules are the only standing cost (about 11.2 € a month, `docs/cost.md`).
- Prompt 06 sets production `minReplicas` to 0 and disables the alert rules without deleting anything.

## Cost per environment

Estimated in `docs/cost.md`. Cost Management, read on 2026-11-02 (data lags up to a day): `rg-juriscope-stg-swc`, tag
`project=product-legal-juriscope`, 0.40 € month to date, almost all Cosmos DB request units from the load test's 4,700 asks,
with no Container Apps charge yet. The shared base (search, models, registry) bills to `rg-aiplatform-shared-swc` and is not split
by product. Production has no cost until phase 8.
