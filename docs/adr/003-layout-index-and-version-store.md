# ADR-003 · Built-in text extraction over the PDF in parts, the BOE version store, and a local push index

**Status:** accepted · **Date:** 2026-11-01

## Context

Juriscope needs two things from the Criminal Code: chunks to search, and the exact article text in every version that was ever in
force. The firm asked for the consolidated PDF to be indexed with Document Intelligence Layout, as its other document pipelines are.
The BOE publishes the same Code as open data, block by block, with every version and its in-force date.

## Options

1. **Search over the BOE blocks only:** one document per article version. Exact, but it is not the client's requested pipeline and
   gives no evidence that the PDF route works for the firm's other documents.
2. **The PDF indexed, and the answer text from the same chunks:** the model would quote chunks that may cut an article in two and
   carry page furniture, and the PDF holds only today's wording.
3. **The PDF indexed for retrieval, the BOE version store for the text** (chosen): search finds the chunks; code maps each chunk to
   the articles it contains and rebuilds them, whole and in the applicable version, from `data/boe/articles.json`.
4. **How the PDF is read:** the Layout skill, as the client asked, or Content Understanding, which Learn now recommends for new
   skillsets, or the indexer's built-in PDF text extraction (chosen). The first staging deploy (2026-11-01) proved the first two
   impossible on the shared search service: Spain Central has no AI enrichment, and it rejects both skillsets with 400 *"Skillset
   contains cognitive services skills which are not supported yet in this region"*. Keyless billing does not add built-in AI
   skills to such a region. A skillset with only `SplitSkill` and the embedding skill is accepted.

## Decision

Option 3, with built-in text extraction. **The client's request for Layout is not met:** it would need a search service in a
region with AI enrichment, and the shared service is in Spain Central. The chunks carry no Markdown headings, which nothing relied on:
code maps chunks to articles by their text, never by a heading.

- **Version store:** `ops/boe.py` builds it from the BOE open-data API (phase 1); it ships in the image.
- **Corpus:** `ops/corpus.py` downloads the consolidated PDF, splits it at *Libro* or *Título* headings into parts under 400,000
  extracted characters (Basic extracts at most 512,000 per file), and uploads them to the environment's `corpus` container with
  the PDF's SHA-256 as metadata. An unchanged PDF uploads nothing.
- **The index and the preamble are left out.** The parts start at the page of *TÍTULO PRELIMINAR*. In phase 1 their 26 chunks mapped to
  no article, which would have held the mapping rate at 95 %.
- **Split measured on 2026-11-01** (207 pages, 716,518 characters with `pypdf`): part 1 is pages 11–117 with 378,457 characters, and
  part 2 is pages 118–207 with 308,498. Over the `pypdf` text of both parts in 2,000-character chunks with 500 overlap, 459 of 459
  chunks map to at least one article. Over the indexed chunks of `jur-articles-stg` (target ≥ 99 %), measured on 2026-11-01 after
  the indexer's first run: 474 of 474 map (100 %), 394 to more than one article.
- **Skillset** `jur-layout-<env>` (`ops/index.py`; the name is kept from the first design, there is no Layout skill inside):
  - `SplitSkill` pages of 2,000 characters with 500 overlap over each part's extracted text;
  - the Azure OpenAI embedding skill (`text-embedding-3-small`, 1,536 dimensions);
  - index projections that skip the parent documents;
  - `headings` stays empty in these chunks;
  - `AIServicesByIdentity` on the shared Foundry account, which bills nothing with no billable built-in skill left; the embedding
    skill calls Foundry with the search identity.
- **Data source and indexer:**
  - the data source reads the container with the search service's identity (Storage Blob Data Reader on the container, from Bicep);
  - deletions are detected through blob soft delete, which is on for seven days;
  - the indexer extracts the text itself (`dataToExtract: contentAndMetadata`), free and available in every region.
- **Local index:** phases 2 to 6 had no storage account, so `jur-articles-local` holds one pushed document per provision in force,
  with the same schema. `docs/evaluation.md` compares it with the staging index in phase 7.

## Consequences

- **Repealed provisions cannot be retrieved.** The staging and production indexes, the local index and `locate` all hold today's
  text. A question whose facts predate a repeal (Book III, repealed in 2015) finds nothing for the repealed provision. The version
  store still has its history. Retrieving it would mean indexing each repealed provision's last version and extending `locate` to it. That is left
  out because the firm's questions concern the Code in force or recently amended articles. The refusal (`no_evidence`) is honest
  about it.
- A Code update is a new image (the version store) plus a new PDF (the index). Both pass the evaluation gate before production.
- A full indexing run costs about 0.01 € of embeddings per environment; text extraction is free. The `deploy.yml` and `release.yml`
  runs repeat it only when the PDF changes.
