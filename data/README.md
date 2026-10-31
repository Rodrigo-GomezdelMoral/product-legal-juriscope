# Data · the Criminal Code version store

`data/boe/` holds every provision of the Spanish Criminal Code with all its versions, as published by the Agencia Estatal Boletín
Oficial del Estado. Juriscope loads it in memory at start-up. The full text of a cited article and the version in force on a date
always come from here, never from the model or from the search index.

| | |
|---|---|
| Publisher | Agencia Estatal Boletín Oficial del Estado (BOE), [www.boe.es](https://www.boe.es) |
| Norm | Ley Orgánica 10/1995, de 23 de noviembre, del Código Penal · `BOE-A-1995-25444` |
| ELI | <https://www.boe.es/eli/es/lo/1995/11/23/10> |
| Official text | <https://www.boe.es/buscar/act.php?id=BOE-A-1995-25444> |
| Source | BOE open-data API, consolidated legislation: `/datosabiertos/api/legislacion-consolidada/id/BOE-A-1995-25444/texto` (XML) and `/metadatos` (JSON) |
| Last update published by the BOE | 2026-04-09 (`fecha_actualizacion`); the last amending norm is Ley Orgánica 1/2026, `BOE-A-2026-7966` |
| Retrieved | 2026-10-30 |

## Reuse conditions

Reused under Ley 37/2007, de 16 de noviembre, sobre reutilización de la información del sector público, and the BOE's
[reuse conditions](https://www.boe.es/informacion/aviso_legal/index.php) (in force since 2024-06-28):

- **Source.** This store extracts and reorders BOE data, so it is cited with the formula the conditions give for modified data,
  *Basado en datos de la Agencia Estatal Boletín Oficial del Estado*, linked to [www.boe.es](https://www.boe.es). Article text shown
  verbatim is cited as *Fuente de los datos: Agencia Estatal Boletín Oficial del Estado*.
- **Informative text.** This is a *texto consolidado de carácter meramente informativo*. Only the BOE's electronic edition is
  official and authentic.
- **Last update.** The BOE's last-update date travels with the data (`updated` in `manifest.json`), so the interface can show it
  with every answer.
- **No endorsement.** The BOE does not take part in, sponsor or endorse Juriscope.
- **Meaning kept and changes identified.** Every change from the source is listed below; none alters the wording of a provision.

## Changes from the source

1. **Only provisions are kept:** blocks of type `precepto` whose title starts with *Artículo* or *Disposición*. Left out are the
   initial note, the preamble, 198 heading blocks (`encabezado`, `Encabezado`, `Cabecera`) and the signature; six headings that the
   BOE types as `precepto` (*TÍTULO XIX bis*, *CAPÍTULO II bis*, a *CAPÍTULO I* and three *SECCIÓN* blocks); and five grouped blocks
   (*Artículos 617 a 622* to *Artículos 638 y 639*) whose only text is "(Derogados)". The history of those articles stays in their
   individual blocks.
2. **Text.** Each version keeps its paragraphs in order, one per line. The heading paragraph ("Artículo 138.") is dropped because it
   always equals the title. Whitespace is collapsed, inline markup (bold, superscripts) is reduced to its text, and empty
   paragraphs are dropped. Two BOE titles carry a trailing space (*Artículo 340 quater* and *quinquies*); it is trimmed.
3. **Notes.** Of the BOE's notes under each version, the store keeps, verbatim, the one that references the version's amending norm
   (for example "Se modifica por el art. único.76 de la Ley Orgánica 1/2015, de 30 de marzo. Ref. BOE-A-2015-3439."). 928 of 1,592
   versions have one. Of the rest, 661 are the original 1995 wording and three cite their norm in another form (articles 42, 445 bis
   and 607).
4. **Order and duplicates.** Versions are sorted by in-force date, because the BOE lists the 1999 versions of articles 181 and 183
   before the 1995 originals. Where the BOE lists two versions with the same in-force date (articles 274, 306, 515, 611 and 631), the
   store keeps the first, the one whose note documents the change.
5. **Repeal date.** The BOE marks 27 articles with `fecha_caducidad`, the day it stops showing them, which is the publication date of
   the repealing law. A repeal takes effect when that law comes into force, so `repealed` is the in-force date of the norm published
   that day (the latest, when its provisions came into force on different days): 2015-07-01 for Book III (articles 617 to 639) and article 576 bis, 2022-10-07 for articles 183 ter and 183 quater, and
   2004-10-01 for article 445 bis.

## Counts on 2026-10-30

| Count | Value | Explanation |
|---|---|---|
| Blocks in the text | 985 | |
| `precepto` blocks | 784 | 750 articles, 23 dispositions, 5 grouped repealed blocks and 6 headings |
| Versions in the whole text | 1,858 | every block type, as in the build prompt |
| Articles | 750 | |
| Articles in force | 723 | 750 minus the 27 repealed, as in the build prompt. 23 of them read only "(Suprimido)", "(Derogado)" or "(Sin contenido)", because a reform emptied them without removing the block, so 700 carry operative text |
| Dispositions | 23 | additional, transitional, repealing and final provisions |
| Provisions stored | 773 | articles and dispositions |
| Versions stored | 1,592 | 1,597 in the stored blocks, less the 5 same-day duplicates |

`articles.json` is 1.9 MB, not the 3 MB first estimated, because it keeps the text and drops the XML markup.

## Provenance of this build

When this store was built, on the evening of 2026-10-30, the BOE open-data API answered HTTP 500 to every route, including the
daily summary, while the website answered normally. The store was therefore built by the same `build()` of `ops/boe.py` from the
API's `texto` and `metadatos` responses fetched earlier that day (HTTP 200, `texto` at 14:47 GMT). `sha256` in `manifest.json` is the hash of
that `texto` response. When the API answers again, `python -m ops.boe` rebuilds both files from it, and an unchanged hash means an
unchanged `articles.json`.

## Files

- **`boe/articles.json`:** the provisions in the order of the Code, each with `block_id`, `title`, `repealed` and its `versions`
  (`norm`, `published`, `in_force`, `text`, `note`), validated on load by `app.models.Article`.
- **`boe/manifest.json`:** norm, title, ELI, source, `updated` (the BOE's last update), `retrieved`, `sha256` of the source text, and
  the counts above.

Links are built from the block id, `https://www.boe.es/buscar/act.php?id=BOE-A-1995-25444#<block id>`. Block ids are not always
`a<number>`: article 142 bis is `a1-2`. A new version of the Code is a new store and a new image, and it passes the evaluation gate
like any other change.
