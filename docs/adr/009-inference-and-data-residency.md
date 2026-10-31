# ADR-009 · Global Standard inference, data at rest in the EU

**Status:** accepted · **Date:** 2026-10-31

## Context

Questions may hold special-category data (GDPR article 10, criminal matters) covered by professional secrecy. The firm wants its
data in the EU. The shared base offers `gpt-5-mini` and `text-embedding-3-small` as Global Standard deployments in
`swedencentral`, and the shared search service runs in `spaincentral`.

## Options

1. **Global Standard** (the shared deployments): data at rest stays in the resource's geography, but a request may be processed
   in any Azure region.
2. **Data Zone EU Standard:** processing stays inside the EU data zone, at about 10 % more per token (build prompt figures,
   2026-10-30), and it needs new deployments and quota in the shared base, which this repository does not own.
3. **Regional Standard** in `swedencentral`: processing in one region, with the narrowest model availability.

## Decision

Option 1 for now, recorded as a trade-off.

- **At rest, in the EU:** Cosmos DB, Storage and Application Insights in `swedencentral`; the search index in `spaincentral`, which
  holds only the public text of the Code and processes the question text there. The history holds questions and answers
  (ADR-002); the model service stores nothing (`store: False`).
- **Processing:** the two agents and the embeddings run on Global Standard and may be processed outside the EU. The interface asks
  lawyers not to paste client identities.
- **Moving to Data Zone EU** is a deployment-name change in the settings (`CHAT_MODEL`, `EMBEDDING_MODEL`) once such deployments
  exist; it passes the evaluation gate like any model change (ADR-010).

## Consequences

- **Cross-region search, measured 2026-10-31:** the app's region (`swedencentral`) is not the search region (`spaincentral`). Over
  19 live answers the `retrieve` step took a median of 0.84 s (0.39 to 2.26 s). That covers the hybrid query with the vectorizer
  embedding the queries and the semantic ranker, plus mapping ten chunks to articles in memory. The first query of a process
  took 3.9 s, cold.
- The search service vectorizes queries with its own identity against the Foundry account (Cognitive Services OpenAI User), so
  the question text also travels from `spaincentral` to the embedding deployment.
