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
| Telemetry | `appi-juriscope-stg-swc`, cap 0.3 GB a day (found at 2.0 GB on 2026-11-03, see *Load tests*) | `appi-juriscope-prod-swc`, cap 1 GB a day |
| Search index | `jur-articles-stg` | `jur-articles-prod` |
| Alerts | declared, disabled | enabled |
| Changed by | `deploy.yml`, on every merge to `main` | `release.yml`, on a published release, after approval |

## Promote, roll back, patch

- **Switch:** `deploy.yml` runs only while the **repository** variable `DEPLOY_ENABLED` is `true`. It cannot be an environment
  variable: a job-level `if` is evaluated before the job's environment exists. `release.yml` does not read it.
- **To staging:** merge a PR to `main`. `deploy.yml` builds the image once, deploys it by digest with `what-if` first, refreshes the
  corpus and the index (a no-op when the PDF is unchanged), checks `/healthz` on the `canary` label and moves all traffic. It then
  runs the smoke test and uploads the digest as the artifact `image-<sha>`.
- **Load test before a release that changes the API:** `gh workflow run load-test.yml --ref main`. It sets the commit status
  `load-test`, naming the digest it tested, that `release.yml` requires. `release.yml` always requires the staging deploy of the
  tagged commit, and skips the load-test requirement only when every path changed since the previous release it promoted matches
  `web/**`, `docs/**`, any `*.md` or `.github/**` (ADR-015); its log prints the changed paths and the decision. With no such
  release, the first one (v1.0.0) included, the load test is required.
- **To production:** `gh release create vX.Y.Z --notes-file <CHANGELOG section>`, then approve the `production` deployment.
  `release.yml` promotes the staging digest of the tagged commit: a smoke test on the `canary` label, 10 % of traffic for twelve
  minutes, then the new revision's requests and 5xx from the Container Apps `Requests` metric, filtered on its revision name. It
  moves to 100 % and deactivates the previous revision, or rolls back when 5xx exceed 1 % of the canary's requests. The job
  summary prints both counts, and says when the canary received no request, which is common at production volume (about 350
  questions a month): the 5xx rule then did not apply and only the smoke test guarded the promotion.
  *Known limitation (release 1.0.1):* the p95 of one revision is not measured. `ResponseTime` has no revision dimension, and in
  Application Insights `cloud_RoleInstance` is a per-process id, so until 1.0.1 the canary query matched nothing and always
  passed. Planned: the app sets `service.instance.id` from the replica name, an `app/` change for the next release with a load
  test.
- **First deployment of an environment:** the Key Vault role and the container app are created in one deployment. If the revision
  fails to read `auth-client-secret` while RBAC propagates, rerun the workflow. Staging avoided it with a temporary Key Vault
  Secrets User on the resource group (`07-staging.sh`), removed after the first revision; later revisions resolve the secret with
  the vault-scoped role alone. Production does the same: the author's `08-production.sh` creates the sign-in app, gives the
  production CI principal `Juriscope.User` (the smoke test calls `/api/meta` with its own token), sets `AUTH_CLIENT_SECRET` and
  `AUTH_CLIENT_ID` in `production` and adds the temporary role before v1.0.0; run again after the release, it adds the sign-in
  callback of the new app, removes the temporary role and opens production in the browser.
- **Rollback, fast path by revision (production, seconds, no redeploy):** the previous release's revision is kept inactive
  (`maxInactiveRevisions: 5`). With `P=ca-juriscope-prod G=rg-juriscope-prod-swc`:
  1. `az containerapp revision list -n $P -g $G --all --query "[].[name, properties.active, properties.trafficWeight]" -o tsv`;
  2. `az containerapp revision activate -n $P -g $G --revision $P--<previous>`, then wait until
     `az containerapp revision show -n $P -g $G --revision $P--<previous> --query properties.healthState -o tsv` is `Healthy`;
  3. `az containerapp ingress traffic set -n $P -g $G --revision-weight $P--<previous>=100 $P--<current>=0`;
  4. check `/healthz` and the `Requests` metric by `revisionName`, then
     `az containerapp revision deactivate -n $P -g $G --revision $P--<current>`.
  The `canary` label stays on the current revision until the next deployment, which rewrites the traffic list. Going forward
  again is the same four steps with the names swapped.
  *Rehearsed in production on 2026-11-03 at 21:32 UTC* (`v1-0-1` to `v1-0-0` and back): the previous revision was healthy 30 s
  after its activation; back in 47 s to `/healthz` 200, forward in 21 s. The `Requests` metric by revision read 21 for `v1-0-0`
  and 0 for `v1-0-1` while rolled back, then 0 and 21. A first rehearsal at 20:28 UTC went back in 58 s.
- **Rollback, planned path (a full redeploy of an earlier release):**
  - staging: `gh workflow run deploy.yml --ref main -f digest=<previous digest>`, then the same with the current digest. Such a
    run uploads its digest as the artifact of `main`'s latest commit, and `release.yml` takes the latest successful run's
    artifact, so a staging drill ends on the current digest before that commit is released;
  - production: `gh workflow run release.yml --ref <latest release tag> -f tag=<previous tag>`, with approval. The workflow runs
    from the ref and deploys the input tag's digest and Bicep as revision `v<major>-<minor>-<patch>-r<run number>`, behind the
    same canary. The ref must be `v1.0.1` or later: earlier tags hold a workflow that reuses the existing revision's suffix, which
    Container Apps rejects. The target commit's `image-<sha>` artifact must still exist (90 days, ADR-012).
  - *Rehearsed on 2026-11-03,* timed from the dispatch to the end of the run. Staging: `deploy.yml` runs 41724016259 (v1.0.0's
    digest, 5 min 26 s) and 41724831402 (v1.0.1's again, 4 min 21 s). Production: `release.yml` runs 41725584657
    (`-f tag=v1.0.0`, revision `v1-0-0-r3`) and 41728213703 (v1.0.1 again, revision `v1-0-1-r4`), 17 min 16 s each way, the
    approval and the twelve-minute canary included; both canaries had 2 requests, 0 with 5xx.
- **Urgent patch (OE:11):** the same path, pre-approved: `feature/hotfix-<what>`, PR with the required checks, merge, staging, load
  test, `vX.Y.Z+1`.
- **Client secret rotation** (the sign-in apps' secrets expire on 2027-11-01, staging, and 2027-11-03, production; rotate in
  October 2027):
  1. add a secret to the sign-in app;
  2. update the environment secret `AUTH_CLIENT_SECRET`;
  3. rerun `deploy.yml` (or `release.yml`): Bicep writes the vault secret and the revision reads its latest version;
  4. delete the old secret.

## Alerts

| Alert | Where | Condition | Who acts and how |
|---|---|---|---|
| `alert-juriscope-prod-5xx` | metric, app | more than 5 server errors in 15 minutes | the author: the workbook's health model, then roll back or scale |
| `alert-juriscope-prod-availability` | log, every 15 min | availability of `/api` below 99.7 % over the last hour, with at least 20 requests | the author: triage by flow (*Ask*, *History*, *Model*) |
| `alert-juriscope-prod-latency` | log, every 15 min | p95 of the ask route at or above 13 s (the latency SLO) over the last hour, with at least 5 questions | the author: *Model* flow, the shared deployment's TPM and the `AnalystRetried` count (ADR-016) |
| `budget-juriscope-<env>` | budget, both environments | 50, 80 and 100 % of 10 € (staging) or 25 € (production) | the author: Cost Management by tag; staging to zero, or production `minReplicas 0` |

Each alert goes to its environment's action group `ag-juriscope-<env>-swc`, which e-mails `ALERT_EMAIL_ADDRESS`. Staging declares the
same rules disabled, so that an enabled log rule never bills there (checked deployed on 2026-11-01: the three rules exist,
disabled). Application Insights adds a *Failure Anomalies* smart detector by itself; it is free and not in Bicep.

Production, 2026-11-03: the action group's test notification was delivered and its e-mail received (22:29 UTC), and
`alert-juriscope-prod-latency` fired for real at 22:52 UTC, when the hour of the walk-through had 6 asks with a p95 of 13.76 s,
and resolved at 00:23 UTC. A staging drill of the same rule could not fire (see *Load tests*); its temporary rule and action
group are deleted.

**Known limitation: in-stream failures are not counted as unavailable** (measured 2026-11-03, release 1.0.1). The availability
tile and alert count `toint(resultCode) >= 500`. The ask route streams, so a turn that fails after the stream started ends with an
`error` event inside an HTTP 200 and counts as available, and its exception is recorded on the span only, not in the console
logs. Staging, 30 days: 31 of 11,304 ask requests (0.27 %) were 200 with `success == false`, all `SearchUnavailableError` after the
shared search service answered 504 under the stress ramps (20 at 08:45–09:15 UTC and 11 at 15:30–16:00 UTC on 2026-11-03).
Production: 0 of 3. Until the fix, read them with `requests | where name has "messages" and success == false`. Planned for the
next release with a load test: `success == false` in the availability tile and alert (`infra/`) and a console line for the
in-stream exception (`app/`). The health model's *Ask* threshold is also stale (6 s, not the 13 s SLO): `PRODUCT.md` §6.

## Backup and restore

- **Cosmos DB:** continuous backup, 7-day tier, point-in-time restore to a new account. RPO 15 minutes, a target with margin:
  Learn (*Continuous backup with point-in-time restore*, 2026-07-13) says all mutations are backed up asynchronously within
  100 seconds, and the drill's restored state was about 25 s behind. The 7-day tier is free. Learn does not state the continuous
  tier for serverless accounts explicitly; the deployed staging account shows `Continuous7Days` on serverless.
- **Restore caveats (Learn):** data-plane role assignments are not restored, so the app's Cosmos DB role is granted again on the
  restored account (Bicep does it on redeploy); the containers keep their 90-day TTL unless the restore passes `--disable-ttl`, so
  items older than 90 days at the restore time expire at once.
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

It then waits for `/healthz` 200 on the stable revision and runs ten minutes at three users on the real model through it, about
90 asks (five minutes until ADR-017). Search is real in every scenario, so semantic queries bill. Promotion goes ahead only if the
real-model p95 of `ask` is under 15,000 ms (SLA-02, restated in ADR-013) and no scenario fails more than 1 %. Since ADR-017 that
p95 is exact: the nearest rank over every real-model ask's response time in `results/real_ask_ms.csv`, not Locust's percentile,
which is rounded to two significant digits (15,000 covers about 14.5 to 15.5 s). The job summary and the status description show
it in milliseconds with the number of asks. Replicas, CPU and memory maxima come from Azure Monitor, for the whole app. Until
release 1.0.1 the query gave only a start time, so Azure CLI read one hour from it, which covered the real-model stage of every
run so far; since 1.0.1 it ends explicitly three minutes after the real-model stage, so that the last minutes are ingested.

| Date | Scenario | Users | Requests/s | p50 | p95 | p99 | Errors | Replicas |
|---|---|---|---|---|---|---|---|---|
| 2026-11-01 | normal, model double | 5 | 0.45 | 1.0 s | 5.1 s | 5.2 s | 0 of 79 | 1 |
| 2026-11-01 | peak, model double | 20 | 1.69 | 1.2 s | 7.7 s | 7.8 s | 0 of 203 | 1 |
| 2026-11-01 | soak, model double | 5 | 0.44 | 0.97 s | 1.4 s | 1.7 s | 0 of 267 | 2 |
| 2026-11-01 | stress, model double | 5 to 100 | 3.47 | 2.3 s | 10 s | 16 s | 0 of 4,159 | 2 (the maximum) |
| 2026-11-01 | real model, cold stable revision | 3 | 0.13 | 9.7 s | 37 s | 37 s | 0 of 14 | 0 → 1 |
| 2026-11-03 | real model, warm stable revision | 3 | 0.14 | 9.5 s | 17 s | 30 s | 0 of 43 | 2 |
| 2026-11-03 | normal, model double | 5 | 0.45 | 1.0 s | 5.3 s | 5.6 s | 0 of 80 | ≤ 2 |
| 2026-11-03 | peak, model double | 20 | 1.71 | 1.2 s | 7.9 s | 8.2 s | 0 of 206 | ≤ 2 |
| 2026-11-03 | soak, model double | 5 | 0.45 | 0.96 s | 1.4 s | 1.8 s | 0 of 270 | ≤ 2 |
| 2026-11-03 | stress, model double | 5 to 100 | 3.14 | 2.7 s | 17 s | 21 s | 17 of 3,761 | 2 (the maximum) |
| 2026-11-03 | **real model, warm, with the *Analyst* deadline** | 3 | 0.15 | 9.3 s | **12 s** | 16 s | 0 of 45 | ≤ 2 |
| 2026-11-03 | real model, warm, phase 8 merge | 3 | 0.15 | 9.5 s | 15 s | 20 s | 0 of 45 | 2 |
| 2026-11-03 | real model, warm, release commit, first run | 3 | 0.15 | 9.1 s | 13.7 s (exact) | 16 s | 1 of 91 | 2 |
| 2026-11-03 | normal, model double | 5 | 0.42 | 1.0 s | 4.8 s | 4.8 s | 0 of 75 | ≤ 2 |
| 2026-11-03 | peak, model double | 20 | 1.61 | 1.4 s | 7.2 s | 7.4 s | 0 of 193 | ≤ 2 |
| 2026-11-03 | soak, model double | 5 | 0.45 | 0.99 s | 1.4 s | 1.8 s | 0 of 270 | ≤ 2 |
| 2026-11-03 | stress, model double | 5 to 100 | 3.26 | 2.7 s | 13 s | 20 s | 11 of 3,908 | 2 (the maximum) |
| 2026-11-03 | **real model, warm, release commit (v1.0.0)** | 3 | 0.16 | 8.6 s | **12.8 s (exact)** | 22 s | 0 of 96 | 2 |

Rates and percentiles are for the ask route at the client (Locust 2.47.0, run 41331036489, digest of `c074a7e`). **The run failed
the SLA-02 gate** as it stood then (p95 < 8 s): the stable revision had idled at zero replicas through the 35 minutes of the
model-double scenarios, and the first three real asks waited 25.5 s for a replica. Server-side, the 15 real asks took 7.2 to
13.7 s (median 9.5 s, p95 13.7 s). The stress ramp never reached 5 % errors: CPU saturated at 0.51 vCPU from about 70 users and
probes timed out in the last two minutes, without a failed ask. Working set peaked at 0.53 GiB, so the replica stays at 0.5 vCPU
and 1 GiB (ADR-008). No dependency returned 429. **The gate is rerun with the warm-up and the longer real-model scenario after the
phase 7 merge, before any release.**

The rerun of 2026-11-03 (run 41603022081) **failed the gate at p95 17 s**, with no failed ask. The two slowest asks (29.7 and 21.7 s)
spent 24.9 and 15.5 s in *Analyst*'s model call, against a median of 3.4 s, on warm replicas. *Analyst* now has a 5-second deadline
and one retry (ADR-016). Count the retries with `customEvents | where name == "AnalystRetried"`. The gate runs again after that change
is deployed to staging.

**The gate passed on 2026-11-03** (run 41619345584, digest of `298ea6a`, the merge of the *Analyst* deadline): 45 real-model asks,
p95 12.0 s against 15 s, 0 failed; normal, peak and soak without errors. The five rows before the last are that run. During the
run the app reached 2 replicas, 0.50 vCPU and 0.55 GiB (maxima over both revisions). The stress ramp reached 100 users; its 17
failures (0.45 %) were streams that ended without an answer or a refusal under CPU saturation, and the stress scenario has no error
gate. Staging telemetry stopped arriving at about 10:50 UTC, during the stress ramp, so the real-model window has almost no spans or
KPI events; that is consistent with the staging daily cap of 0.3 GB, which this run did not confirm. The client-side figures
above do not depend on it. `release.yml` requires the `load-test` status on the tagged commit, so the gate runs again on the
phase 8 merge commit before v1.0.0.

The run on the phase 8 merge commit (2026-11-03, run 41637405127, `0550f3f`, the same app code as `298ea6a`) **failed the gate at
Locust's p95 15,000 ms**: 45 real-model asks, median 9.5 s, maximum 19.9 s, 0 failed; 2 replicas, 0.51 vCPU and 0.53 GiB at
most. With 45 asks the p95 is the 3rd slowest ask, and Locust's 15,000 is a bucket from about 14.5 to 15.5 s, so this run and the
12,000 of `298ea6a` are consistent with the same code measured too coarsely on too few asks. ADR-017 makes the gate read the exact p95 and doubles
the real-model stage to ten minutes. The gate runs again on that change's merge commit before v1.0.0.

On the release commit `b8dd5e1` (2026-11-03), run 41650046759 **failed**: exact p95 13,745 ms on 91 real-model asks, but 1 ask ended
in an in-stream `error` event, above the 1 % rule for 91 asks; its cause was never confirmed. **Run 41661582947 passed** on the
same commit and digest (registry tag `20261103-main-b8dd5e1`, stable revision `--r12-1`), the digest v1.0.0 promoted: exact p95
12,784 ms on 96 asks (recomputed from `real_ask_ms.csv`), median 8.6 s, maximum 22.1 s, 0 failed; normal, peak and soak without
errors; the stress ramp's 11 failed asks (0.28 %) were the `SearchUnavailableError` streams of *Alerts*; 2 replicas, 0.51 vCPU
and 0.52 GiB at most. The last seven rows of the table are these two runs, and run 41661582947 is the SLA-02 evidence of v1.0.0.

**Known limitation: staging telemetry during load tests.** The staging Application Insights daily cap is 0.3 GB, reset at
00:00 UTC, and is kept. The model-double scenarios of the morning run filled it at about 10:50 UTC on 2026-11-03, so run
41637405127 has no spans or KPI events. The gate reads client-side times and does not depend on telemetry; explaining a slow
ask does. Run a load test that may need diagnosis as the first of its UTC day, and check the cap in the portal before reading
spans. On 2026-11-03 the staging cap was found at 2.0 GB, set by hand after the 13:49 UTC deploy and outside Bicep. The next
`deploy.yml` sets it back to 0.3 GB (its `what-if` deploys `pricingPlans/current`); the author's housekeeping script checks it.

**Known limitation: staging telemetry gap on 2026-11-03** (read 2026-11-04). Staging Application Insights holds nothing after the
18:00 UTC hour of 2026-11-03, although the console logs show the alert drill's question answered with 200 between 22:30 and
22:35 UTC. `deploy.yml` restored the daily cap to 0.3 GB at 19:30 UTC on a day that had already ingested more (the stress
ramps), so ingestion stopped until the 00:00 UTC reset. That, not the rule, is why the staging alert drill could not fire. The
rule above applies to anything that needs staging telemetry after a cap change on a busy day: run it first in its UTC day.

## DORA

Read from the Actions runs with `gh run list --workflow deploy.yml` and `--workflow release.yml`, with dates:
- deployment frequency;
- lead time from merge to staging and from tag to production;
- change failure rate (failed or rolled-back releases);
- time to restore.

| Window | Deployment frequency | Lead time | Change failure rate | Time to restore |
|---|---|---|---|---|
| Staging, 2026-11-01 | 3 `deploy.yml` runs with a result, 2 successful (one commit, `c074a7e`) | PR #10: 5 min from merge (12:06) to staging (12:11), 12 min from opening | 1 of 3 (11:37, the Layout skill rejected in Spain Central) | 34 min, restored by PR #10 |
| Staging, 2026-11-01 to 2026-11-03 | 15 `deploy.yml` runs with a result, 13 successful (2 of them the rollback drill's dispatches, 21:41 and 21:46 on 11-03) | 5 to 8 min from merge to staging (PRs #10 to #19 and #24) | 2 of 15 (11-01 11:37, the Layout skill; 11-02 19:42, the runner's managed identity endpoint) | 34 min and 17 min |
| Production, 2026-11-03 | 2 releases (v1.0.0 and v1.0.1, `release.yml` succeeded, approval recorded) and 2 rollback dispatches rehearsed (runs 41725584657 and 41728213703, both successful) | v1.0.0: 8 min from tag (16:28) to production (16:36), 2 h 46 min from merge (13:49), the load test included. v1.0.1: 18 min from tag (19:45) to production (20:03), 33 min from merge (19:30), the approval and the canary included | 0 of 2 releases | no incident; rehearsed: 47 s by revision, 17 min 16 s by a planned redeploy |

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
by product. On 2026-11-03 the Cost Management query API answered 429 to the reads by the `environment` tag, so production's first
month is read after the release, by `08-production.sh`'s summary or in the portal, by the `project` and `environment` tags.

**Advisor, 2026-11-03, after v1.0.0:** staging: *increase the minimal replica count* (Medium), by design (staging scales to zero,
ADR-008); *enable zone redundancy for storage accounts* (High), rejected in ADR-011: the `corpus` container holds the public PDF,
downloaded again from the BOE by `ops/corpus.py`; *enable zone redundancy for the managed environment* (High), rejected in
ADR-014. Production: no recommendation.
