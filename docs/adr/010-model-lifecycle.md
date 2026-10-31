# ADR-010 · Model versions, settings and retirement

**Status:** accepted · **Date:** 2026-10-31

## Context

Both agents need a reasoning model with structured output; the subscription has quota for `gpt-5-mini` and none for
`gpt-5-nano`. Shared deployments are pinned (`NoAutoUpgrade`), so a retired version answers `410 Gone` instead of changing
behaviour silently.

## Decision

- **Models:** `gpt-5-mini` version `2025-08-07` for *Analyst* and *Counsel*, and `text-embedding-3-small` version 1 for the index
  and its vectorizer, all Global Standard. Retirement dates read from the Models API on 2026-10-31: **2027-02-09** for
  `gpt-5-mini` and **2028-02-09** for the embeddings.
- **Settings** (`app/agents.py`): `reasoning.effort` `low`, no temperature or `top_p` (reasoning models reject them), `store: False`,
  and `max_tokens` 800 for *Analyst* and 3,000 for *Counsel*, reasoning tokens included. Over 19 live answers the largest outputs
  were 488 and 1,293 tokens. The client has an explicit 60-second timeout; the OpenAI SDK keeps its default retries.
- **Prompts** are files (`app/prompts/analyst_v1.md`, `counsel_v1.md`); a change is a new file and passes the gate (phase 3).
- **Replacement:** Microsoft names the replacement about 90 to 120 days before retirement (Learn, model lifecycle, 2026-07-24).
  The change is one deployment name in the settings, and it must pass the full evaluation suite against the baseline in
  `docs/evaluation.md`.

## Consequences

- **Latency against SLA-02, measured 2026-10-31:** 19 live answers took a median of 10.7 s end to end (7.4 to 15.6 s), and only
  4 of 19 finished under 8 s. Steps: *Analyst* median 2.9 s, `retrieve` 0.8 s, *Counsel* 6.0 s, `verify` 0.02 s.
- **`reasoning.effort: "minimal"` is accepted by this deployment,** contrary to the build prompt's note. On four questions
  it took 4.5 to 10.1 s against 9.1 to 9.8 s at `low`, and *Counsel*'s output tokens roughly halved. One answer was visibly
  shorter. Its effect on recall, citation precision and groundedness is unmeasured, so the effort stays `low` until the phase 3
  gate compares both.
- **Cost per answered question, measured:** median 0.0046 € (0.0042 to 0.0062 €), the semantic query included at its list price.
  Median tokens: *Analyst* 566 in and 249 out, *Counsel* 3,638 in and 777 out.
