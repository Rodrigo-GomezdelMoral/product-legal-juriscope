# ADR-005 · Structured output, deterministic verification, typed refusal

**Status:** accepted · **Date:** 2026-10-31

## Context

REQ-01 asks that every statement cites an article retrieved for the question, and REQ-04 that the product refuses rather than
answer from model knowledge. A prompt can ask for both; only code can guarantee them.

## Options

1. **Free text with inline citation marks**, parsed afterwards. Fragile, and a claim without a mark cannot be told apart from a
   sentence of connective text.
2. **An LLM judge** that checks the draft. Another model call, another cost, and still a model deciding.
3. **Structured output and a deterministic check.** *Counsel* returns `Draft(claims=[Claim(text, article_ids)])` through
   `response_format`; code keeps only the claims whose `article_ids` are non-empty and a subset of the articles retrieved for
   this question.

## Decision

Option 3.

- **Models:** *Analyst* returns `LegalQuery` (`question`, its restatement of the lawyer's question; `scope`, one of
  `criminal_code`, `case_law`, `other_law` and `not_legal`; `search_queries`, `facts_date`, `language`); *Counsel* returns
  `Draft`. Both through the framework's `response_format`, which the Responses API enforces as a strict JSON schema.
- **Verification** (`compose` in `app/workflow.py`): unverified claims are dropped and counted (`dropped_claims`, the K2 KPI). The
  answer is composed from the verified claims only, numbered by first citation, and every citation carries the full article from
  the BOE version store, never text from the model. Citation marks the model writes into a claim are removed before numbering.
- **Typed refusal** with three reasons:
  - `out_of_scope`: *Analyst* says the Code cannot answer; the search is never called. The refusal carries *Analyst*'s `scope`
    (`case_law`, `other_law` or `not_legal`), a value from a fixed list that the interface words. Until phase 4 the reason was
    a sentence written by the model, and the gate found the canary copied into it; a typed value cannot carry it.
  - `no_evidence`: *Analyst* gives no search query, no article is retrieved, no claim survives verification, or *Counsel*
    returns no claims.
  - `content_filter`: the shared guardrail or the model declined. This covers `ChatClientContentFilterException` (a prompt
    blocked with HTTP 400 when not streaming), `finish_reason == "content_filter"` (a completion cut by the filter), and a reply
    that is not JSON at all. The last case was found live: on the streaming structured-output path, a prompt that the
    guardrail blocks comes back as the plain text "I'm sorry, but I cannot assist with that request.", which the OpenAI SDK
    fails to parse and Agent Framework wraps in a generic `ChatClientException`. `declined()` treats that exception as a refusal
    only when its cause is a `json_invalid` validation error on text that does not start with `{`.
- **Errors stay errors:** truncated or invalid JSON, a field the schema rejects, a reply cut by `max_tokens` (`finish_reason`
  `length`), a run that ends with no outcome, and every other client error, a `429` included, raise. None of them is reported
  to the lawyer as a refusal. The API turns them into RFC 9457 problem responses with the trace id: a rate limit (`RateLimitError`
  after the SDK's own retries, or the shared deployment's in-stream rejection, which the SDK cannot retry) is a `503` with the
  `Retry-After` the service sent, or 20 s when it sent none; an unavailable search or Cosmos DB, a connection failure or a model
  timeout, a `503`; a request the model service rejects (any other 4xx) or an unusable reply (`UnusableReplyError`: truncation,
  invalid output, no outcome), a `502` without `Retry-After`, because repeating it would not help.

## Consequences

- Guardrail measurement (2026-10-31): `guardrail-chat` blocks Hate, Sexual, Violence and Self-harm at medium on prompt and
  completion, with Prompt Shields for jailbreak and Protected Material text and code (the indirect-attack shield for documents
  is not configured). Over 16 questions it blocked none of the 10 general questions, none of three on violent offences (murder
  with ensañamiento, injuries with weapons, genital mutilation) and none on adult sexual assault. It blocked both questions on
  sexual offences against minors (sexual acts with minors under 16, production of child sexual abuse material) on every attempt,
  eight of eight through the workflow. The prompt filter rated them **Sexual: high**, so a policy that blocks only at high would
  still block them. Framing the system prompts as professional legal research did not change the result and was removed.
- These questions get a clear `content_filter` refusal instead of an error. Answering them would need a deployment whose content
  filter configuration Microsoft has approved for this use, which the shared base does not have; `RESPONSIBLE_AI.md` (phase 3)
  records the limitation.
- The step that raises a content-filter exception reports no token usage, so that refusal's `cost_eur` leaves out the
  blocked call; the steps before it are counted.
