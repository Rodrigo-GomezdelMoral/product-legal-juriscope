# ADR-013 · SLA-02 restated from the staging measurements

**Status:** accepted (author's decision) · **Date:** 2026-11-02

## Context

SLA-02 promised 95 % of standard questions answered in under 8 s, from the request to the final server-sent event, and the latency
SLO was p95 < 6 s. Phase 7 measured the deployed workflow in staging, with `gpt-5-mini` at `low` effort for both agents:

- **Browser, one user (2026-11-01, 4 answers):** 8.3 to 12.9 s from sending to the final state on screen; *Analysing the question*
  within 10 to 27 ms, because the client shows it as soon as the question is sent.
- **Spans, first session:** *Analyst* 2.5 s, `retrieve` p50 0.83 s, *Counsel* p50 5.2 s and p95 7.5 s, `verify` 4 ms. *Counsel*
  alone nearly fills 8 s.
- **`load-test.yml` run of 2026-11-01, real-model scenario (3 users, 2 minutes, 14 asks):** p50 9.7 s, p95 37 s at the client. The
  37 s was a cold start, not the model: the stable revision had sat idle at zero replicas through the 35 minutes of the model-double
  scenarios, and the first three asks waited 25.5 s for a replica (image pull, container start) and took 36 to 37 s in all. With
  14 samples those three are everything above p80. Server-side, all 15 real asks took 7.2 to 13.7 s, median 9.5 s, p95 13.7 s;
  *Counsel* p50 4.1 s and p95 8.0 s.
- **Full evaluation suite on `jur-articles-stg` (2026-11-01, 82 answered, four concurrent):** p50 8.4 s, p95 12.3 s.

Production keeps one warm replica (ADR-008), so the gate measured a cold start production never shows. Without it, 8 s is still out
of reach while *Counsel*'s own p95 is 7.5 to 8.0 s.

## Options

1. **Both agents at `minimal` effort:** p95 8.2 s on the full suite (2026-10-31), but correct refusal fell to 0.80, groundedness to
   0.878 and the canary leaked (ADR-010). It failed the gate with the v2 prompts and would need a full-suite run with v4 and v5.
2. **A non-reasoning model for *Counsel*:** a new deployment in the shared base, outside this repository, and a full-suite run
   against the baseline.
3. **Restate SLA-02 from evidence** (chosen): 95 % under 15 s to the final event, plus the progress line within 0.1 s; the gate
   measures a warm revision for long enough to have a p95.

## Decision

Option 3.

- **SLA-02:** 95 % of standard questions answered in under 15 s, from the request to the final server-sent event, and *Analysing the
  question* on screen within 0.1 s of sending (measured in the browser).
- **Latency SLO:** p95 < 13 s for the ask route, keeping the 2 s gap under the SLA that the old pair (6 and 8 s) had. The workbook
  tile, the production latency alert and `release.yml`'s canary check use it.
- **`load-test.yml`:** waits for `/healthz` 200 on the stable revision before the real-model scenario, which now runs 5 minutes at 3
  users (about 35 asks, about 0.2 € of tokens) instead of 2. The gate fails at p95 ≥ 15,000 ms or more than 1 % failed asks.
- **The gate is rerun after the phase 7 merge, before any release.** The 2026-11-01 run stays recorded as failed in
  `OPERATIONS.md`.

## Consequences

- The value case does not move: a 10 to 13 s answer against the 30 to 75 minutes that steps 2 to 6 take by hand leaves K1's target
  (10 minutes to an accepted answer) untouched.
- `minimal` effort stays a measured experiment for later, through the full suite against the baseline in `docs/evaluation.md`
  (ADR-010); if it passes, SLA-02 can tighten again.
- A slower shared deployment (other load on the shared 100K TPM) shows up first as an SLO miss in the workbook and the latency
  alert, before the SLA.
