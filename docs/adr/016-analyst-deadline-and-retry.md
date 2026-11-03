# ADR-016 · A 5-second deadline and one retry for *Analyst*

**Status:** accepted (author's decision) · **Date:** 2026-11-03

## Context

The SLA-02 gate (ADR-013) was rerun on staging on 2026-11-03 (`load-test.yml`, real-model stage, 3 users for 5 minutes on a warm
revision). It recorded 43 asks with 0 failures and a client p95 of 17,000 ms, against a 15,000 ms gate. The client percentiles were
p50 9.5 s, p90 14 s and p95 17 s, and the slowest ask took 29.7 s.

- **The two slowest asks** (29.7 s and 21.7 s) came mid-stage, with 2 warm replicas, so they were not cold starts.
- **In both, *Analyst*'s `chat gpt-5-mini` span** took 24.9 s and 15.5 s, with 239 and 179 output tokens. *Analyst*'s median is
  3.4 s and 251 tokens, so the slow calls were not longer reasoning.
- **In the 15.5 s call, the HTTP response started at 2.9 s;** the rest was the stream. The client's 60-second timeout (ADR-010) is an
  httpx read timeout, applied between chunks, so it never bounds a slow stream as a whole.
- **Other steps:** *Counsel* p95 7.5 s, search 0.6 s, Cosmos DB under 0.1 s. The deployment is Global Standard in the shared base.
- **Staging telemetry over the two days to 2026-11-03** (Application Insights, chat spans under `invoke_agent analyst`): 56 *Analyst*
  calls, p50 3.4 s, p95 11.1 s, input p50 888 tokens, output p50 251 and p95 386. Only 3 calls took longer than 8 s, and all 3 took
  longer than 11 s; 4 took longer than 5 s. The tail is a few very slow calls, not a broad slope.

The cause is latency variance on the model side, which a prompt or code change in Juriscope cannot remove. A second call for the same
input usually returns at the median.

## Options

1. **Rerun the gate unchanged** and hope the tail does not recur: 2 slow calls in 43 asks already move p95, and nothing would change
   the next time.
2. **`reasoning.effort: "minimal"` for *Analyst*:** faster on average, but it changes the restatement (`Answer.question`) that the
   groundedness judge reads, and `minimal` failed the gate on correct refusal and groundedness in phase 3 (ADR-010). It would also
   not stop a slow stream.
3. **Restate SLA-02 again:** it was restated from evidence the day before (ADR-013); widening it to fit one run's tail would make it
   follow the measurements instead of what the lawyers need.
4. **A total deadline on *Analyst* with one retry** (chosen). At 8 s a retried ask would take about 8 + 3.4 + 4.8 to 6.2 ≈ 16.2
   to 17.6 s, still above 15 s; 5 s keeps it under 15 s and cuts only one more call of 56 (4 instead of 3).

## Decision

Option 4. *Counsel* keeps its current settings.

- **First attempt:** *Analyst*'s whole run, streaming included, is bounded by `ANALYST_DEADLINE_SECONDS = 5` in `app/agents.py`.
- **Retry:** when the deadline passes, the attempt is cancelled and the run is repeated once.
- **Second attempt:** no deadline beyond the client's 60-second timeout, so a request never fails only because the model is slow.
- **Where:** an agent middleware (`deadline`, `@agent_middleware`) on the *Analyst* agent. It wraps `call_next()` and the
  consumption of the resulting stream in `asyncio.timeout`, so the deadline covers the time to the first byte and the whole stream.
  The middleware runs inside the workflow's `analyze` step, so the phase events, the history and the routing are unchanged.
- **Untouched:**
  - The OpenAI SDK's own retries (connection errors, retryable statuses) happen inside each attempt.
  - Every other error propagates as before: rate limits, the in-stream rejection, content filtering and connection failures. So the
    API's 503 and 502 mapping (ADR-005) and the evaluation runner's retry of `APIConnectionError` still apply.
- **Telemetry:** each retry logs the custom event `AnalystRetried` on the `juriscope` logger. It reaches Application Insights as a
  `customEvents` row with the request's operation id: `customEvents | where name == "AnalystRetried" | count`. Count retries with
  this event, not with spans: how the cancelled attempt's spans end has not been checked live.
- **Tests:** `test_slow_analyst_is_cut_and_retried_once` sets the deadline to 0.1 s and makes the first attempt take 1 s and return an
  out-of-scope query, so an answer proves the second attempt's result was used. The question must finish within 0.9 s, and the
  second attempt, at 0.3 s, must not be cut.

## Cost

At most one extra *Analyst* call per question, only when the deadline fires. At the price in `docs/cost.md` (0.22 € in and 1.76 € out
per million tokens), a full call costs about 888 × 0.22 / 10⁶ + 251 × 1.76 / 10⁶ ≈ **0.0006 €**. The cancelled call costs at most
as much as a full one. That is an upper bound of about 12 % of the 0.0052 € median per answer,
on retried questions only. At the rate the telemetry shows for 5 s (4 of 56 calls, about 7 %), it is about 0.00004 € per question on
average, about 0.015 € a month at 350 questions; even if every question retried it would be 0.22 € a month. The 0.05 € per-question SLO does not
move. The cancelled call's usage never reaches `AnswerDelivered.cost_eur`, because usage arrives at the end of the stream, so the
workbook's cost per question slightly understates retried questions. The extra prompt, about 900 tokens, is negligible against the
shared deployment's 100K TPM.

## Consequences

- **Expected effect, not yet measured:** a retried ask takes the deadline plus a second *Analyst* call plus the rest of the
  workflow. With the median second call (3.4 s), the two slow asks of 2026-11-03 would have taken about 5 + 3.4 + 4.8 ≈ 13.2 s and
  5 + 3.4 + 6.2 ≈ 14.6 s instead of 29.7 s and 21.7 s, so a retried ask lands just under 15 s. A slow second call, or a slow
  *Counsel* in the same ask, can still pass 15 s. The `ONLY=load` rerun after the merge measures it.
- **About 7 % of questions retry** at the rate the telemetry shows (4 of 56 calls over 5 s). A call that would have finished between
  5 and 6 s now takes 5 s plus a second call; the telemetry shows one such call in 56.
- **Analyst's p95 per call no longer describes a question's latency:** the workbook's request p95 and the `AnalystRetried` count do.
- **The evaluation suite** runs through `Juriscope.ask`, so it gets the same deadline; its latency figures include retries from now on.
