import hashlib
import json
from datetime import date
from xml.etree.ElementTree import Element

import httpx
from defusedxml import ElementTree

from app.corpus import ARTICLE, DATA
from app.models import ARTICLES, Article, ArticleVersion

API = "https://www.boe.es/datosabiertos/api/legislacion-consolidada/id/BOE-A-1995-25444"
KEPT = (ARTICLE, "Disposición ")


def fetch(path: str, accept: str) -> bytes:
    response = httpx.get(f"{API}/{path}", headers={"Accept": accept}, timeout=120)
    response.raise_for_status()
    return response.content


def clean(element: Element) -> str:
    return " ".join("".join(element.itertext()).split())


def version(node: Element) -> ArticleVersion:
    norm = node.get("id_norma", "")
    body = [clean(p) for p in node.findall("p") if p.get("class") != "articulo"]
    notes = [clean(p) for p in node.findall("blockquote/p")]
    return ArticleVersion(
        norm=norm,
        published=date.fromisoformat(node.get("fecha_publicacion", "")),
        in_force=date.fromisoformat(node.get("fecha_vigencia", "")),
        text="\n".join(paragraph for paragraph in body if paragraph),
        note=next((note for note in notes if norm in note), None),
    )


def article(block: Element, in_force_of: dict[str, str]) -> Article:
    first_per_day = {parsed.in_force: parsed for parsed in reversed([version(n) for n in block.findall("version")])}
    expiry = block.get("fecha_caducidad")
    return Article(
        block_id=block.get("id", ""),
        title=block.get("titulo", "").strip(),
        repealed=date.fromisoformat(in_force_of.get(expiry, expiry)) if expiry else None,
        versions=sorted(first_per_day.values(), key=lambda v: v.in_force),
    )


def counts(blocks: list[Element], articles: list[Article]) -> dict[str, int]:
    single = [a for a in articles if a.title.startswith(ARTICLE)]
    return {
        "blocks": len(blocks),
        "precepts": sum(block.get("tipo") == "precepto" for block in blocks),
        "versions": sum(len(block.findall("version")) for block in blocks),
        "articles": len(single),
        "articles_in_force": sum(a.repealed is None for a in single),
        "dispositions": len(articles) - len(single),
        "stored": len(articles),
        "stored_versions": sum(len(a.versions) for a in articles),
    }


def build(metadata: bytes, text: bytes, retrieved: date) -> tuple[list[Article], dict[str, object]]:
    meta = json.loads(metadata)["data"][0]
    blocks = ElementTree.fromstring(text).findall("./data/texto/bloque")
    nodes = [node for block in blocks for node in block.findall("version")]
    in_force_of = dict(sorted((n.get("fecha_publicacion", ""), n.get("fecha_vigencia", "")) for n in nodes))
    kept = [b for b in blocks if b.get("tipo") == "precepto" and b.get("titulo", "").startswith(KEPT)]
    articles = [article(block, in_force_of) for block in kept]
    return articles, {
        "norm": meta["identificador"],
        "title": meta["titulo"],
        "eli": meta["url_eli"],
        "source": f"{API}/texto",
        "updated": date.fromisoformat(meta["fecha_actualizacion"][:8]).isoformat(),
        "retrieved": retrieved.isoformat(),
        "sha256": hashlib.sha256(text).hexdigest(),
        "counts": counts(blocks, articles),
    }


def write(articles: list[Article], manifest: dict[str, object]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "articles.json").write_bytes(ARTICLES.dump_json(articles, indent=1) + b"\n")
    (DATA / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    articles, manifest = build(fetch("metadatos", "application/json"), fetch("texto", "application/xml"), date.today())
    write(articles, manifest)
    print(json.dumps(manifest["counts"]))


if __name__ == "__main__":
    main()
