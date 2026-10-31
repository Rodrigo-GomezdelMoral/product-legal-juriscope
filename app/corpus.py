import bisect
import itertools
import re
from datetime import date
from pathlib import Path

from app.models import ARTICLES, Article, ArticleVersion, Citation, Reference

DATA = Path(__file__).resolve().parent.parent / "data" / "boe"
OFFICIAL = "https://www.boe.es/buscar/act.php?id=BOE-A-1995-25444#"
ARTICLE = "Artículo "
NUMBER = r"\d+(?: (?:bis|ter|qu[aá]ter|quinquies|sexies|septies|octies))?\b"
ITEM = re.compile(rf"({NUMBER})(?:\.\d+)*( a )?")
LIST = rf"{NUMBER}(?:\.\d+)*(?:(?:, | y | o | a ){NUMBER}(?:\.\d+)*)*"
MENTION = re.compile(rf"\b[Aa]rt(?:ículos?|s?\.) ((?>{LIST}))(?! (?:de la|del) (?!Código Penal)[A-ZÁÉÍÓÚ])")
RELATIVE = re.compile(r"\b[Aa]rtículo (anterior|precedente|siguiente)\b")
WINDOW = 12


def normalise(text: str) -> str:
    return " ".join(re.findall(r"\w+", text.lower()))


class Corpus:
    def __init__(self, articles: list[Article]) -> None:
        self.articles = {article.block_id: article for article in articles}
        self.numbers = {a.title.removeprefix(ARTICLE): a.block_id for a in articles if a.title.startswith(ARTICLE)}
        current = {block_id: self.version_at(block_id, date.today()) for block_id in self.articles}
        parts = [normalise(f"{self.articles[b].title} {v.text}") for b, v in current.items() if v]
        self.ids = [block_id for block_id, version in current.items() if version]
        self.starts = list(itertools.accumulate([len(part) + 1 for part in parts[:-1]], initial=1))
        self.text = f" {' '.join(parts)} "

    @classmethod
    def load(cls) -> "Corpus":
        return cls(ARTICLES.validate_json((DATA / "articles.json").read_bytes()))

    def version_at(self, block_id: str, at: date) -> ArticleVersion | None:
        article = self.articles[block_id]
        if article.repealed and at >= article.repealed:
            return None
        return next((version for version in reversed(article.versions) if version.in_force <= at), None)

    def references(self, block_id: str, at: date) -> list[str]:
        version = self.version_at(block_id, at)
        if version is None:
            return []
        order, enacted = self.order(at), self.order(version.in_force)
        found = [b for match in MENTION.finditer(version.text) for b in self._expand(match.group(1), order)]
        if block_id in enacted:
            position = enacted.index(block_id)
            for match in RELATIVE.finditer(version.text):
                neighbour = position + (1 if match.group(1) == "siguiente" else -1)
                found += enacted[neighbour : neighbour + 1] if neighbour >= 0 else []
        return [b for b in dict.fromkeys(found) if b != block_id and b in order]

    def order(self, at: date) -> list[str]:
        return [block_id for block_id in self.numbers.values() if self.version_at(block_id, at)]

    def _expand(self, mention: str, order: list[str]) -> list[str]:
        found: list[str] = []
        start: str | None = None
        floor = 0
        for number, to in ITEM.findall(mention):
            value = int(number.split()[0])
            block_id = self.numbers.get(number) if value >= floor else None
            floor = max(floor, value)
            if block_id is None or block_id not in order:
                start = None
                continue
            found += order[order.index(start) : order.index(block_id) + 1] if start else [block_id]
            start = block_id if to else None
        return found

    def reference(self, block_id: str) -> Reference:
        return Reference(block_id=block_id, title=self.articles[block_id].title, url=OFFICIAL + block_id)

    def cite(self, block_id: str, at: date | None = None) -> Citation | None:
        today = date.today()
        version = self.version_at(block_id, at or today)
        if version is None:
            return None
        current = self.version_at(block_id, today)
        return Citation(
            **self.reference(block_id).model_dump(),
            version=version,
            current=None if current == version else current,
            repealed=self.articles[block_id].repealed,
            see_also=[self.reference(b) for b in self.references(block_id, at or today)],
        )

    def locate(self, chunk: str) -> list[str]:
        words = normalise(chunk).split()
        hits: list[int] = []
        last = max(len(words) - WINDOW, 0)
        for i in {*range(0, last + 1, WINDOW), last}:
            window = f" {' '.join(words[i : i + WINDOW])} "
            at = self.text.find(window)
            if at >= 0 and at == self.text.rfind(window):
                hits += [at + 1, at + len(window) - 2]
        if not hits:
            return []
        first, last = (bisect.bisect_right(self.starts, hit) - 1 for hit in (min(hits), max(hits)))
        return self.ids[first : last + 1]
