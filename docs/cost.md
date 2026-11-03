# Cost

Estimated in EUR from the Azure Retail Prices API (`api-version=2023-01-01-preview`). Model, search, Cosmos DB and log prices were
read on 2026-10-30; the Container Apps prices again on 2026-11-01 for Spain Central and on 2026-11-02 for France Central (ADR-014). These are **estimates**; staging's measured figures are below,
from Cost Management by the `project` tag, and the workbook shows the cost per question from `AnswerDelivered`. The
free Container Apps grant is not counted, because other apps in the subscription already use it.

## Container Apps in France Central

The apps run in France Central since 2026-11-02 (ADR-014). The API rounds EUR prices to six decimals.

| Meter | France Central (2026-11-02) | Sweden Central (2026-11-02) | Spain Central (2026-11-01) |
|---|---|---|---|
| vCPU active, € per second | 0.000022 | 0.000022 | 0.000030 |
| vCPU and memory idle, € per second (vCPU or GiB) | 0.000003 | 0.000003 (0.00000264 in the build prompt's estimate) | 0.000004 |

France Central matches Sweden Central at the API's precision; Spain Central is about **42 % dearer**. The idle rate used below is
the build prompt's 0.00000264 € per vCPU-second or GiB-second.

## Per environment, per month

| Item | Staging at rest | Staging in use | Production at rest | Production in use |
|---|---|---|---|---|
| Container Apps (0.5 vCPU, 1 GiB) | 0 | 0.24 (30 sessions × 10 min) | 10.3 (one idle replica, ADR-008; at most 11.7) | 10.3 |
| Tokens (`gpt-5-mini`: 0.22 € in, 1.76 € out per 1M) | 0 | 0.50 (100 questions) | 0 | 1.75 (350 questions) |
| Semantic ranker (first 1,000 a month free per service, then 1.76 € per 1,000) | 0 | ≤ 0.18 | 0 | ≤ 0.62 |
| Cosmos DB serverless (0.268 € per million RU, 0.22 €/GB), Blob, Key Vault | ≈ 0.06 | ≈ 0.08 | ≈ 0.06 | ≈ 0.10 |
| Log alert rules (0.44 € per rule a month, enabled in production only) | 0 | 0 | 0.88 | 0.88 |
| Logs (2.63 €/GB after the billing account's free 5 GB) | 0 | ≤ 1.3 | 0 | ≤ 1.3 |
| **Total** | **≈ 0.1 €** | **≈ 1.0 € (≤ 2.3)** | **≈ 11.2 €** | **≈ 13.0–15.0 €** |

The 5xx metric alert rule (one time series) is not priced here; it is disabled in staging, so Cost Management shows it only
from the first release.

## Per question

- **Variable:**
  - estimated at about 0.007 €: tokens about 0.005 € plus up to 0.0018 € of semantic ranking;
  - measured in phase 2 at a median of 0.0046 € (0.0042 to 0.0062 €, 19 answers, semantic query at list price).
- **All-in in production at 350 questions a month:** (11.2 + 350 × 0.0046 to 0.007) ÷ 350 ≈ **0.037 to 0.039 €**, against the 0.05 € SLO.
  - In Spain Central (until 2026-11-02) it was 0.049 to 0.051 €.
  - Measured in phase 7 (2026-11-01): a median of 0.0052 € per answer in the browser (5), 0.0051 € in the load test's real-model
    scenario (15) and 0.0049 € over the full evaluation suite; a refusal 0.0007 €. All-in: (11.2 + 350 × 0.0052) ÷ 350 ≈
    **0.037 €** in France Central (0.0495 € in Spain Central).
  - The replica stays at 0.5 vCPU / 1 GiB: the load test peaked at 0.53 GiB and 0.51 vCPU, so 0.25 vCPU / 0.5 GiB (about 0.03 €
    per question) is not safe (ADR-008).

## One-off

- **Full indexing:** about 0.01 € of embeddings per environment; the indexer's PDF text extraction is free (no Layout skill, ADR-003).
  It is repeated only when the PDF changes.
- **Full load test:** about 2–4 € of semantic queries, plus about 0.45 € of tokens for the 10-minute real-model scenario (about 90
  answers at 0.0051 €; 0.2 € more than the 5-minute scenario before ADR-017, with about 0.1 € more of semantic queries). The run
  of 2026-11-01 (about 4,700 asks) also cost about 0.40 € of Cosmos DB request units.

## Measured in staging (Cost Management, read 2026-11-02)

- `rg-juriscope-stg-swc`, tag `project=product-legal-juriscope`: 0.40 € month to date (2026-11-01), of which Cosmos DB 0.399 €,
  Key Vault, Storage and bandwidth under 0.001 € each. No Container Apps charge appears yet. The data lags up to a day.
- The shared base, 2026-11-01: AI Search 5.68 €, Foundry models 0.85 €, Foundry tools 0.70 €, registry 0.15 €. It is not split by
  product; the search figure includes that day's semantic queries from every product, this load test's among them.
- Production: nothing until the first release (phase 8).

## Shared base

Billed even when idle, and not counted per environment:
- AI Search Basic in Spain Central: 64.88 € a month (0.0889 €/h);
- registry Basic: 4.46 € a month.

That is 69.34 € a month for the shared base as a whole.

Traffic from France Central to Sweden Central and Spain Central (the app's calls to the models, Cosmos DB, Key Vault, Application
Insights and the search service, and the image pull) is a few KB per question. At 350 questions a month it is far below 1 GB, which costs cents at most.

## Switching off

- **What bills when stopped:** production's warm replica (about 10.3 €) and its two enabled log alert rules (0.88 €).
- **Staging** scales to zero by itself, and its alert rules are disabled.
- **Production to zero without deleting anything** (prompt 06): `minReplicas: 0` and the alert rules disabled.
- **No spending limit:** the subscription is pay-as-you-go, so budgets only alert. `OPERATIONS.md` says who reacts and how.
