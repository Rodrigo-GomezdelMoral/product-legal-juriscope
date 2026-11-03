# ADR-017 · The SLA-02 gate reads the exact p95 of a 10-minute real-model stage

**Status:** accepted (author's decision) · **Date:** 2026-11-03

## Context

`release.yml` requires the `load-test` status on the tagged commit (ADR-015), so the gate ran again on the phase 8 merge commit
(`0550f3f`, run 41637405127). Its real-model stage, 3 users for 5 minutes on the warm stable revision, recorded 45 asks with
0 failures, a median of 9.5 s, a maximum of 19.9 s and a Locust p95 of 15,000 ms. The gate is `real_p95 -lt 15000`, so it failed.
The same stage on the previous main commit (`298ea6a`, run 41619345584) passed with 45 asks, the same median and a p95 of 12,000 ms.
Between the two commits only the demo fixtures, the evidence panel and the documentation changed; the app code is the same.

- **Locust rounds before it computes percentiles.** It stores each response time rounded to two significant digits (to the
  nearest 100 ms from 1 s, to the nearest 1,000 ms from 10 s) and reads percentiles from those buckets. A CSV value of 15,000 means
  the ask at the p95 rank took anywhere from about 14.5 s to 15.5 s. The gate could not tell a pass from a fail at the threshold.
- **45 asks are a small sample.** The nearest-rank p95 of 45 is the 43rd fastest, the 3rd slowest ask. One slow ask more or less
  moves p95 by several seconds: 12 s and 15 s are the same code on two runs.
- **No telemetry for this run.** The model-double scenarios of the morning run filled the staging Application Insights daily cap
  (0.3 GB, reset at 00:00 UTC) at about 10:50 UTC, so there are no server-side spans to explain the slow asks.

## Options

1. **Rerun the gate unchanged:** the next run could pass or fail on the same code, and a pass would be a 15,000 bucket on the
   right side by chance. Nothing would be learnt and the release would rest on rounding.
2. **Cut latency further** (a shorter *Analyst* deadline, a different effort, a smaller prompt): without telemetry there is no
   evidence of which step was slow in the three slowest asks, so any change would be a guess, and each costs an evaluation run.
3. **Restate SLA-02 again:** rejected for the same reason as in ADR-016; the threshold follows the lawyers' need, not one run.
4. **Measure exactly, on a larger sample** (chosen).

## Decision

Option 4, with the threshold (15,000 ms) and the failure rule (at most 1 % of asks failed) unchanged.

- **Exact p95.** In the real scenario only, `load/locustfile.py` appends each ask's response time, as Locust measured it, in whole
  milliseconds, to `results/real_ask_ms.csv`. Failed asks are included, as in Locust's own percentiles. `load-test.yml` sorts the
  file and takes the nearest-rank p95, the value at rank ⌈0.95 × n⌉, with `awk`. The gate requires that p95 under 15,000 ms and
  the file's count equal to Locust's ask count, so no ask is missing from the sample. Locust's CSV and HTML are kept as before.
- **A 10-minute stage.** The real-model stage runs 10 minutes instead of 5, still at 3 users (`SHAPES["real"] = (3, 600)`),
  about 90 asks. The p95 rank becomes the 86th of 90, the 5th slowest ask, so a single slow model call moves it much less.
- **Reporting.** The job summary and the `load-test` status description show the exact p95 in milliseconds and the number of asks,
  e.g. `p95 14812 ms of 90 asks (SLA 15000)`.
- **Timeout.** The job's worst case grows from about 47 to 52 minutes (stress at its 20-minute limit), inside the existing
  `timeout-minutes: 90`.

Checked locally: the `awk` line against a Python ⌈0.95 × n⌉ reference for n from 1 to 101, and on synthetic samples built to the
two saved real-model CSVs. With 45 asks and Locust's 15,000, the 3rd slowest ask at 14,501 ms passes and at 15,499 ms fails.
A short local Locust run wrote one line per ask, matching Locust's request count.

## Cost

About 45 more real-model asks per load test: about 0.2 € of tokens (45 × 0.0051 €) and about 0.1 € of semantic queries
(1.76 € per 1,000), so a full load test costs about 2.3 to 4.3 € instead of 2 to 4 €. The run takes about 5 minutes longer.
Nothing changes in production.

## Consequences

- A gate result is no longer decided by Locust's rounding; a run near the threshold reads, for example, 14,812 ms or 15,140 ms.
- Results before this ADR were read from Locust's rounded CSV and stay as recorded (12 s, 15 s, 17 s, 37 s).
- The staging cap stays at 0.3 GB. A second load test in the same UTC day runs without telemetry: the gate does not depend on it,
  but the diagnosis of a slow ask does. It is a known limitation in `docs/OPERATIONS.md`.
