# ADR-002 · Conversation history with the native Cosmos DB provider, model storage off

**Status:** accepted · **Date:** 2026-10-31

## Context

REQ-06 asks that a lawyer can resume a conversation and that a follow-up question uses its context. The model must see the
earlier turns; the sidebar must list a user's conversations and render their turns with citations; deleting a conversation must
remove all of it. Questions may hold special-category data (GDPR article 10), so nothing should be stored that the product does
not need, and nothing should be stored by the model service.

## Options

1. **Server-side history in the model service** (`store: True`, previous response ids). No storage of our own, but the
   conversation then lives in the shared Foundry account, outside the environment's data boundary, with no TTL we control.
2. **A hand-written history table** in Cosmos DB. Full control, but it reimplements what Agent Framework ships.
3. **`CosmosHistoryProvider`** from `agent-framework-azure-cosmos` for the model's context, plus a `conversations` container for
   the sidebar and the rendered turns (phase 4), both in the environment's own Cosmos DB account.

## Decision

Option 3, with `store: False` on every model call.

- **The package is beta** (`1.0.0b261015`), so it is pinned exactly and installed with the rest of the set; Dependabot groups the
  `agent-framework-*` packages so they move together.
- **What the history holds:** for each answered turn, the question and the answer text with a closing line of sources
  (`Sources: [1] Artículo 138; …`), so that a follow-up such as "the next article" can be resolved. The retrieved articles are
  passed to *Counsel* inside the workflow and are never persisted; the version store rebuilds them.
- **The agents see the last ten messages** (five turns) of a conversation, so the cost of a question does not grow with the
  length of the conversation.
- **Refusals are not saved to the history.** A follow-up after a refusal starts without it, and, above all, a question blocked by
  the content filter is never sent back to the model on the next turn, where it would be blocked again.
- **The provider gets a `container_client`.** Given only a database, it calls `create_container_if_not_exists`, which the data
  plane role (Cosmos DB Built-in Data Contributor) does not allow. Bicep creates the `history` container (`/session_id`,
  `defaultTtl` 90 days) in phase 6; locally it is created once in the emulator.
- **`list_sessions()` is not used:** it is a cross-partition query with no user filter. The `conversations` container, partitioned
  by `/user_id`, lists and authorises; `session_id` is checked for ownership before the history is read (phase 4).
- **Locally**, the Cosmos DB vNext emulator (`vnext-EN20261019`, pinned by digest in the `Makefile`) runs over HTTP. `azure-core`
  refuses to send a bearer token to a non-TLS URL, so the local client uses a key, which the emulator does not check; every Azure
  environment uses the managed identity with local auth disabled.

## Consequences

- Live check (2026-10-31, emulator): "¿Qué pena tiene el homicidio?" and then "¿Y si concurre alevosía?" in the same session, the
  second asked through a fresh `Juriscope` and provider. *Analyst* received 1,032 input tokens instead of about 560, the answer cited
  article 139 (murder with alevosía), and the container held four messages.
- `clear(session_id)` deletes a conversation's history; phase 4 calls it with the record deletion (REQ-06).
- Retention is the container TTL (REQ-10), not a job.
