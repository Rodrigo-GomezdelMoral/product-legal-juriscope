# ADR-001 · A graph workflow with two agents, run directly with explicit history

**Status:** accepted · **Date:** 2026-10-31

## Context

A question goes through four steps: understand it (scope, search queries, date of the facts), search the Code, draft cited
claims, and check every citation. The flow branches to a refusal at two points: when the question is outside the Code, which must
not reach the search, and when nothing retrieved supports a claim. The interface shows progress per step (ADR-004), and a
follow-up question needs the earlier turns.

Two of the steps need language understanding: reading a lawyer's question, with the conversation, into Spanish search queries and
a date; and writing claims from the articles. Searching, choosing the version in force, mapping chunks to articles and checking
citations are deterministic, and the guide's rule applies to them: if it can be written as a function, write a function
(`microsoft-agent-framework-guide.md` 0.1).

## Options

1. **One function calling the model twice.** Fewest lines, but the two refusal branches, the progress events and the history
   are all hand-written control flow.
2. **One agent with tools** (search, versions). The model would decide whether to search and what to cite, which is exactly what
   the product must not delegate: retrieval is decided by code and citations are checked by code (ADR-005).
3. **A graph workflow** (`WorkflowBuilder`, guide 3.2): `analyze` and `draft` as `AgentExecutor`s (3.7), `retrieve`, `verify`
   and `refuse` as function executors (3.3), conditional edges for the branches (3.4), built fresh per request (3.6).

For the history, the build prompt asked for `workflow.as_agent(name="juriscope", context_providers=[history])` (guide 6.4), with a
fallback if per-step events did not surface through it.

## Decision

Option 3, in `app/workflow.py`:

- `analyze` (agent *Analyst*) → `retrieve` when its `scope` is `criminal_code`, → `refuse` otherwise, so an out-of-scope question never reaches the
  search. `retrieve` → `draft` (agent *Counsel*) or → `refuse` when no article is found; `draft` → `verify` → the answer, or →
  `refuse` when no claim survives. The edges out of `retrieve` and `verify` carry no condition: the framework delivers a message
  only to the targets whose handler accepts its type, so an `AgentExecutorRequest` reaches `draft` and a `Refusal` reaches
  `refuse`.
- **Only *Analyst* reads the conversation and the lawyer's words.** *Counsel* receives one message: *Analyst*'s restatement of the
  question, the language, the date of the facts and the retrieved articles (phase 4, decision approved by the author on
  2026-10-31). An instruction written in the question has to survive the restatement to reach the drafter, and, since
  `analyst_v4.md`, code removes every passage *Analyst* lists in `left_out` from the restatement and drops a claim that repeats
  one ([ADR-005](005-structured-output-and-verification.md)).
- **The workflow is run with `workflow.run(..., stream=True)`, not through `as_agent`,** and `Juriscope.ask` loads and saves the
  history itself with the provider's `get_messages` and `save_messages`. This is the fallback the build prompt allowed, chosen on
  evidence from the installed `agent-framework-core` 1.23.0:
  - `WorkflowAgent` forwards only `output`, `intermediate`, `data` and `request_info` events (`AGENT_FORWARDED_EVENT_TYPES`).
    Custom events (guide 3.5) and `executor_invoked` stay inside the workflow.
  - `intermediate` outputs do cross the boundary, but they are merged into the agent response, and the history provider's
    `after_run` stores that response. A scratch run with `InMemoryHistoryProvider` stored each progress payload as an assistant
    message next to the answer, so every follow-up would have sent the progress lines back to the model.
  - Run directly, the workflow streams every event, and the history holds exactly what ADR-002 wants: the question and the final
    answer text.
- **Progress comes from the framework:** `executor_invoked` of `analyze`, `retrieve`, `draft` and `verify` becomes a phase, and
  `retrieve` yields one intermediate output with the number of articles read. No step emits progress by hand.
- **Usage and cost per question** come from the `AgentExecutorResponse`s carried by `executor_completed`, plus one semantic query
  when `retrieve` runs (`app/config.py` holds the prices).

## Consequences

- The workflow is the graph in the README: five executors and six edges, each branch a declared edge with a test
  (`tests/test_workflow.py`).
- Content-filter outcomes escape the graph as exceptions from the agent executors; `ask` turns them into the typed refusal of
  ADR-005, so `refuse` handles only the reasons the graph itself decides.
- If a later framework release forwards custom events through `as_agent` and lets history skip intermediate outputs, the switch is
  local to `Juriscope.ask`.
