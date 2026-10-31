# ADR-004 · Stream progress, not tokens

**Status:** accepted · **Date:** 2026-10-31

## Context

An answer takes several seconds: on 2026-10-31, 19 live answers took a median of 10.7 s, of which *Counsel* took a median of 6.0 s.
A lawyer waiting that long needs to see that the system is working. The usual remedy is to stream the model's tokens.

Here the model's output is a JSON list of claims (ADR-005), and `verify` removes any claim whose citations were not retrieved for
the question. Streaming tokens would show the lawyer raw JSON and, worse, claims that verification is about to remove.

## Options

1. **Stream tokens** of the draft and correct the screen after verification.
2. **No streaming:** one response at the end.
3. **Stream progress:** one event per step, then the verified answer or the refusal as a single event.

## Decision

Option 3. `Juriscope.ask` yields `PhaseEvent`s (`analysing`, `searching`, `reading` with the number of articles, `drafting`,
`verifying`) and then one `Answer` or `Refusal`. The API sends them over SSE with FastAPI's own `EventSourceResponse` and
`ServerSentEvent` (keep-alive comments included): `phase` events, then one `answer` or `refusal` carrying the conversation id and
the saved turn. The interface shows the progress line *Analysing the question · Searching the Code · Reading n articles ·
Drafting · Verifying citations*.

**The response starts once *Analyst* has replied.** An HTTP status cannot change after the first byte, so the API runs the
ownership check, the history read and the first model call before it answers. A failure there is a problem response with its
real status: a model rate limit is a `503` with `Retry-After`, an unavailable search or Cosmos DB a `503`. A failure after the
first byte (a rate limit on *Counsel*, the search) ends the stream with an `error` event carrying the same problem document; the
request span is marked failed and the exception recorded, so the availability SLI can count it although the status was 200. The
interface shows *Analysing the question* as soon as it sends, because that step always comes first. Measured locally on
2026-10-31 (six questions in two runs, shared models): the first byte arrived after 1.9 to 9.0 s, the analysis step.

The phases come from the workflow's own `executor_invoked` events, plus the article count that `retrieve` yields (ADR-001). The
agent executors still stream their model calls internally, because the workflow runs in streaming mode, but their updates are not
designated as workflow output and never leave the graph.

## Consequences

- Nothing on screen is ever withdrawn: the first claim the lawyer reads has already been verified.
- Perceived latency is the whole run. SLA-02 (95 % of answers under 8 s, to the final event) is therefore a property of the full
  pipeline, and the phase 2 measurements put it at risk (ADR-010).
