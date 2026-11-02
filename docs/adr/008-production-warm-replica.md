# ADR-008 · One warm replica in production

**Status:** accepted · **Date:** 2026-11-01

## Context

SLA-02 asked for 95 % of standard questions answered in under 8 s (15 s since 2026-11-02, ADR-013). The workflow already takes a median of 6.3 to 6.8 s with a warm
process (phase 4). A cold replica adds image pull, Python start-up, loading the 3 MB version store and the first search query
(3.9 s cold in phase 2). The firm works Monday to Friday, 08:00–21:00 Europe/Madrid.

Container Apps prices in Spain Central (Retail Prices API, 2026-11-01) are about 42 % above Sweden Central. The API rounds EUR to six
decimals, so the ratio comes from the active vCPU meter: 0.000030 against 0.000021 € per second, and 0.000034 against 0.000024 $.
Since 2026-11-02 the apps run in France Central (ADR-014), whose meters match Sweden Central's at the API's precision.

## Options

1. **`minReplicas: 1`** (chosen): one replica of 0.5 vCPU and 1 GiB billed at the idle rate when it serves nothing, about 10.3 € a
   month in France Central and Sweden Central (14.6 € in Spain Central). At most 11.7 € if the idle meter is really the rounded 0.000003 €.
2. **A cron scale rule for business hours:** a replica held by a scale rule bills at the active rate, about 19.3 € a month in Spain
   Central for the business hours alone. It also conflicts with multiple revision mode, which the canary needs.
3. **Scale to zero:** free at rest, but every first question of the morning, and after each idle period, pays the cold start against
   SLA-02.

## Decision

Option 1 in production, `minReplicas: 0` in staging. Staging measures the cold start, which tells whether option 3 could ever be
acceptable. Measured in phase 7: 30.1 s for the first request after scaling to zero (2026-11-01, one user), and in the load test
the first three real-model questions waited 25.5 s for a replica (scale-out decision 0.3 s, image pull from 15 s, container started
at 16.5 s, first request served at 25.5 s) and took 36 to 37 s in all. Option 3 is ruled out, and `load-test.yml` now warms the stable revision before measuring
SLA-02, as production's warm replica does.

## Consequences

- The warm replica is production's main standing cost. With the two log alert rules, production costs about 11.2 € a month at rest (15.5 € in Spain Central).
- **All-in cost per question at 350 questions a month is about 0.037 to 0.039 €,** against the 0.05 € SLO. The variable part is
  0.0046 to 0.007 € per question.
  - In Spain Central it was about 0.049 to 0.051 €.
  - **Size kept at 0.5 vCPU / 1 GiB (phase 7, 2026-11-01).** Azure Monitor maxima per revision: working set 0.36 GiB at start,
    0.40 GiB at 3 users on the real model and at 20 users on the model double, 0.53 GiB at 100 users; CPU 0.08 vCPU at 3 users,
    0.22 vCPU at 20 users, 0.51 vCPU (saturated, probe timeouts, no failed request) at 100 users. 0.25 vCPU / 0.5 GiB would sit
    at the CPU limit at the peak scenario and run out of memory under stress, so the saving (about 7.3 €) is not taken.
  - The workbook shows the figure month by month.
- Prompt 06 sets `minReplicas: 0` to switch production off without deleting it.
