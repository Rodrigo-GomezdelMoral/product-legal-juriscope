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
- **Prompts** are files; a change is a new file and passes the gate. Phase 3 replaced `analyst_v1.md` and `counsel_v1.md` with
  `analyst_v2.md` and `counsel_v2.md` after the gate's first run, and phase 4 added `analyst_v3.md` and `counsel_v3.md`
  (*Analyst* restates the question and types the scope; *Counsel* reads only the restatement). `counsel_v4.md` followed in
  phase 4, when the required `eval` check failed on over-citation: *Counsel* chooses the fewest articles that answer the
  question before it writes, and leaves out other offences, other forms and general rules the question does not ask about
  ([evaluation.md](../evaluation.md)).
- **Replacement:** Microsoft names the replacement about 90 to 120 days before retirement (Learn, model lifecycle, 2026-07-24).
  The change is one deployment name in the settings, and it must pass the full evaluation suite against the baseline in
  `docs/evaluation.md`.

## Consequences

- **Latency against SLA-02, measured 2026-10-31:** 19 live answers took a median of 10.7 s end to end (7.4 to 15.6 s), and only
  4 of 19 finished under 8 s. Steps: *Analyst* median 2.9 s, `retrieve` 0.8 s, *Counsel* 6.0 s, `verify` 0.02 s.
- **`reasoning.effort: "minimal"` is accepted by this deployment,** contrary to the build prompt's note, and the phase 3 gate
  compared it with `low` on the full suite on 2026-10-31 (prompt v2, 110 cases each). `minimal` cut the median time per
  question from 7.6 s to 4.6 s and p95 from 12.4 s to 8.2 s. But correct refusal fell from 1.00 to 0.80, groundedness from
  0.964 to 0.878, and citation precision from 0.695 to 0.603, and the canary leaked in 2 of 15 adversarial cases against 1.
  **The effort stays `low`.** SLA-02 is measured under load in phase 7; if it fails there, the levers are the brief's size
  and a faster model, through the gate, not a lower effort.
- **Cost per answered question, measured:** median 0.0046 € (0.0042 to 0.0062 €), the semantic query included at its list price.
  Median tokens: *Analyst* 566 in and 249 out, *Counsel* 3,638 in and 777 out.
