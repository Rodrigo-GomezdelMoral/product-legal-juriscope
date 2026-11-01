# Cost

Estimated in EUR from the Azure Retail Prices API (`api-version=2023-01-01-preview`). Model, search, Cosmos DB and log prices were
read on 2026-10-30; the Container Apps prices again on 2026-11-01 for Spain Central. These are **estimates**. Phase 7 measures them by
the `project` and `environment` tags in Cost Management, and the workbook shows the cost per question from `AnswerDelivered`. The
free Container Apps grant is not counted, because other apps in the subscription already use it.

## Container Apps in Spain Central

The API rounds EUR prices to six decimals.

| Meter | Spain Central | Sweden Central |
|---|---|---|
| vCPU active, € per second | 0.000030 | 0.000021 |
| vCPU active, $ per second | 0.000034 | 0.000024 |
| vCPU and memory idle, € per second (vCPU or GiB) | 0.000004 | 0.000003 (0.00000264 in the build prompt's estimate) |

Spain Central is about **42 % dearer**. The idle rate used below is 0.00000264 × 1.42 ≈ 0.00000375 € per vCPU-second or GiB-second.

## Per environment, per month

| Item | Staging at rest | Staging in use | Production at rest | Production in use |
|---|---|---|---|---|
| Container Apps (0.5 vCPU, 1 GiB) | 0 | 0.34 (30 sessions × 10 min) | 14.6 (one idle replica, ADR-008; at most 15.6) | 14.6 |
| Tokens (`gpt-5-mini`: 0.22 € in, 1.76 € out per 1M) | 0 | 0.50 (100 questions) | 0 | 1.75 (350 questions) |
| Semantic ranker (first 1,000 a month free per service, then 1.76 € per 1,000) | 0 | ≤ 0.18 | 0 | ≤ 0.62 |
| Cosmos DB serverless (0.268 € per million RU, 0.22 €/GB), Blob, Key Vault | ≈ 0.06 | ≈ 0.08 | ≈ 0.06 | ≈ 0.10 |
| Log alert rules (0.44 € per rule a month, enabled in production only) | 0 | 0 | 0.88 | 0.88 |
| Logs (2.63 €/GB after the billing account's free 5 GB) | 0 | ≤ 1.3 | 0 | ≤ 1.3 |
| **Total** | **≈ 0.1 €** | **≈ 1.1 € (≤ 2.4)** | **≈ 15.5 €** | **≈ 17.3–19.3 €** |

The 5xx metric alert rule (one time series) is not priced here. Phase 7 reads it from Cost Management.

## Per question

- **Variable:**
  - estimated at about 0.007 €: tokens about 0.005 € plus up to 0.0018 € of semantic ranking;
  - measured in phase 2 at a median of 0.0046 € (0.0042 to 0.0062 €, 19 answers, semantic query at list price).
- **All-in in production at 350 questions a month:** (15.5 + 350 × 0.0046 to 0.007) ÷ 350 ≈ **0.049 to 0.051 €**, against the 0.05 € SLO.
  - With Container Apps in Sweden Central it would be about 0.04 €.
  - The margin depends on the warm replica (ADR-008): a 0.25 vCPU / 0.5 GiB replica, if phase 7's load test shows it is enough,
    brings it to about 0.03 €.

## One-off

- **Full indexing:** about 0.01 € of embeddings per environment; the indexer's PDF text extraction is free (no Layout skill, ADR-003).
  It is repeated only when the PDF changes.
- **Full load test:** about 2–4 € of semantic queries, plus about 0.25 € for the real-model scenario.

## Shared base

Billed even when idle, and not counted per environment:
- AI Search Basic in Spain Central: 64.88 € a month (0.0889 €/h);
- registry Basic: 4.46 € a month.

That is 69.34 € a month, shared by P05 to P08.

Traffic between Spain Central and Sweden Central (the app's calls to the models, Cosmos DB, Key Vault and Application Insights, and
the image pull) is a few KB per question. At 350 questions a month it is far below 1 GB, which costs cents at most.

## Switching off

- **What bills when stopped:** production's warm replica (about 14.6 €) and its two enabled log alert rules (0.88 €).
- **Staging** scales to zero by itself, and its alert rules are disabled.
- **Production to zero without deleting anything** (prompt 06): `minReplicas: 0` and the alert rules disabled.
- **No spending limit:** the subscription is pay-as-you-go, so budgets only alert. `OPERATIONS.md` says who reacts and how.
