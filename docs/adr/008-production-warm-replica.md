# ADR-008 · One warm replica in production

**Status:** accepted · **Date:** 2026-11-01

## Context

SLA-02 asks for 95 % of standard questions answered in under 8 s. The workflow already takes a median of 6.3 to 6.8 s with a warm
process (phase 4). A cold replica adds image pull, Python start-up, loading the 3 MB version store and the first search query
(3.9 s cold in phase 2). The firm works Monday to Friday, 08:00–21:00 Europe/Madrid.

Container Apps prices in Spain Central (Retail Prices API, 2026-11-01) are about 42 % above Sweden Central. The API rounds EUR to six
decimals, so the ratio comes from the active vCPU meter: 0.000030 against 0.000021 € per second, and 0.000034 against 0.000024 $.

## Options

1. **`minReplicas: 1`** (chosen): one replica of 0.5 vCPU and 1 GiB billed at the idle rate when it serves nothing, about 14.6 € a
   month in Spain Central (10.26 € in Sweden Central). At most 15.6 € if the idle meter is really the rounded 0.000004 €.
2. **A cron scale rule for business hours:** a replica held by a scale rule bills at the active rate, about 19.3 € a month in Spain
   Central for the business hours alone. It also conflicts with multiple revision mode, which the canary needs.
3. **Scale to zero:** free at rest, but every first question of the morning, and after each idle period, pays the cold start against
   SLA-02.

## Decision

Option 1 in production, `minReplicas: 0` in staging. Staging measures the cold start, which tells whether option 3 could ever be
acceptable.

## Consequences

- The warm replica is production's main standing cost. With the two log alert rules, production costs about 15.5 € a month at rest.
- **All-in cost per question at 350 questions a month is about 0.049 to 0.051 €,** against the 0.05 € SLO. The variable part is
  0.0046 to 0.007 € per question.
  - Before the move to Spain Central it was about 0.04 €.
  - Phase 7 measures the replica's CPU and memory under load. If 0.25 vCPU and 0.5 GiB are enough, they halve this cost (about
    7.3 €).
  - The workbook shows the figure month by month.
- Prompt 06 sets `minReplicas: 0` to switch production off without deleting it.
