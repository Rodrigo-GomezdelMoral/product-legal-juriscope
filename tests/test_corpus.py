import json
from datetime import date

import pytest

from app.corpus import DATA, OFFICIAL, Corpus
from app.models import Article, ArticleVersion

ORIGINAL = ("BOE-A-1995-25444", date(1996, 5, 24))
REFORM_2015 = ("BOE-A-2015-3439", date(2015, 7, 1))
HOMICIDE = (
    "1. El que matare a otro será castigado, como reo de homicidio, con la pena de prisión de diez a quince años.\n"
    "2. Los hechos serán castigados con la pena superior en grado en los siguientes casos:\n"
    "a) cuando concurra en su comisión alguna de las circunstancias del apartado 1 del artículo 140, o\n"
    "b) cuando los hechos sean además constitutivos de un delito de atentado del artículo 550."
)


@pytest.fixture(scope="module")
def corpus() -> Corpus:
    return Corpus.load()


def history(corpus: Corpus, block_id: str) -> list[tuple[str, date]]:
    return [(version.norm, version.in_force) for version in corpus.articles[block_id].versions]


def at(corpus: Corpus, block_id: str, day: date) -> ArticleVersion:
    version = corpus.version_at(block_id, day)
    assert version is not None
    return version


def synthetic(texts: dict[str, str]) -> Corpus:
    since = date(2000, 1, 1)
    return Corpus(
        [
            Article(
                block_id=f"a{number}",
                title=f"Artículo {number}",
                versions=[ArticleVersion(norm="BOE-A-2000-1", published=since, in_force=since, text=text)],
            )
            for number, text in texts.items()
        ]
    )


def test_store_follows_the_build_rules(corpus: Corpus) -> None:
    counts = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))["counts"]
    articles = list(corpus.articles.values())
    assert counts["stored"] == len(articles)
    assert counts["stored_versions"] == sum(len(article.versions) for article in articles)
    assert all(article.title.startswith(("Artículo ", "Disposición ")) for article in articles)
    assert all([v.in_force for v in a.versions] == sorted({v.in_force for v in a.versions}) for a in articles)
    assert history(corpus, "a181")[0] == ORIGINAL
    assert "Ley Orgánica 15/2003" in (at(corpus, "a274", date(2005, 1, 1)).note or "")


def test_articles_138_and_139_versions(corpus: Corpus) -> None:
    assert history(corpus, "a138") == history(corpus, "a139") == [ORIGINAL, REFORM_2015]
    assert "Ley Orgánica 1/2015" in (corpus.articles["a139"].versions[-1].note or "")


def test_full_article(corpus: Corpus) -> None:
    citation = corpus.cite("a138")
    assert citation is not None
    assert (citation.title, citation.version.text) == ("Artículo 138", HOMICIDE)
    assert citation.url == "https://www.boe.es/buscar/act.php?id=BOE-A-1995-25444#a138"
    assert (citation.version.norm, citation.version.in_force) == REFORM_2015
    assert citation.current is None and citation.repealed is None


def test_version_at(corpus: Corpus) -> None:
    assert corpus.version_at("a139", date(1996, 5, 23)) is None
    for day in (date(2014, 5, 15), date(2015, 6, 30)):
        assert "de quince a veinte años" in at(corpus, "a139", day).text
    assert "de quince a veinticinco años" in at(corpus, "a139", date(2015, 7, 1)).text
    citation = corpus.cite("a139", date(2014, 5, 15))
    assert citation is not None and citation.current is not None
    assert (citation.version.norm, citation.version.in_force) == ORIGINAL
    assert (citation.current.norm, citation.current.in_force) == REFORM_2015


def test_repealed_article(corpus: Corpus) -> None:
    assert corpus.articles["a617"].repealed == date(2015, 7, 1)
    last = at(corpus, "a617", date(2015, 6, 30))
    assert (last.norm, last.in_force) == ("BOE-A-2003-21538", date(2004, 10, 1))
    assert corpus.version_at("a617", date(2015, 7, 1)) is None
    assert corpus.cite("a617") is None
    citation = corpus.cite("a617", date(2015, 6, 30))
    assert citation is not None and citation.current is None and citation.repealed == date(2015, 7, 1)


def test_142_bis_lives_in_block_a1_2(corpus: Corpus) -> None:
    assert corpus.numbers["142 bis"] == "a1-2"
    citation = corpus.cite("a1-2")
    assert citation is not None and citation.title == "Artículo 142 bis"
    assert citation.url == "https://www.boe.es/buscar/act.php?id=BOE-A-1995-25444#a1-2"
    assert history(corpus, "a1-2") == [("BOE-A-2019-2973", date(2019, 3, 3))]
    assert corpus.version_at("a1-2", date(2019, 3, 2)) is None


def test_references(corpus: Corpus) -> None:
    citation = corpus.cite("a138")
    assert citation is not None
    assert [(r.title, r.url) for r in citation.see_also] == [
        ("Artículo 140", OFFICIAL + "a140"),
        ("Artículo 550", OFFICIAL + "a550"),
    ]
    assert corpus.references("a1-2", date.today()) == ["a152", "a142"]
    assert corpus.references("a67", date.today()) == ["a66"]
    assert corpus.references("a138", date(2000, 1, 1)) == []


def test_reference_rules() -> None:
    corpus = synthetic(
        {
            "1": "Véanse los artículos 2 a 4 y el artículo 9 de la Ley Orgánica 5/2000.",
            "2": "Conforme a los apartados del artículo 8.2 y 3 del presente Código.",
            "3": "Véase el artículo siguiente.",
            "4": "Lo dispuesto en el artículo anterior y en el artículo 4.",
            "5": "Según los artículos 2 y 3 de la Ley 25/1964.",
            "8": "",
            "9": "",
        }
    )
    day = date(2001, 1, 1)
    assert corpus.references("a1", day) == ["a2", "a3", "a4"]
    assert corpus.references("a2", day) == ["a8"]
    assert corpus.references("a3", day) == ["a4"]
    assert corpus.references("a4", day) == ["a3"]
    assert corpus.references("a5", day) == []


def test_chunk_spanning_two_articles(corpus: Corpus) -> None:
    homicide = at(corpus, "a138", date.today()).text
    murder = at(corpus, "a139", date.today()).text
    note = "Se modifica por el art. único.76 de la Ley Orgánica 1/2015, de 30 de marzo. Ref. BOE-A-2015-3439."
    assert corpus.locate(f"{homicide[-240:]}\n{note}\n### Artículo 139.\n{murder[:240]}") == ["a138", "a139"]
    tail = " ".join(murder.split()[:20])
    assert corpus.locate(f"{' '.join(homicide.split()[-39:])} {note} Artículo 139. {tail}") == ["a138", "a139"]
    assert corpus.locate(f"Artículo 139. {murder[:200]}") == ["a139"]
    assert corpus.locate(" ".join(at(corpus, "a274", date.today()).text.split()[30:150])) == ["a274"]
    assert corpus.locate("BOLETÍN OFICIAL DEL ESTADO\nLEGISLACIÓN CONSOLIDADA\nPágina 45") == []
