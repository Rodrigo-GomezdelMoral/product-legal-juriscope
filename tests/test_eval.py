from collections import Counter
from datetime import date

import httpx2
import pytest
from agent_framework.exceptions import ChatClientException
from openai import APIError, APIStatusError

from app.corpus import Corpus, normalise
from app.models import Answer, Citation, Refusal
from eval.evaluators import Case, Observed
from eval.run import THRESHOLDS, gate, load, measure, passes, report, throttled

SIZES = {"golden": 60, "versions": 15, "unanswerable": 20, "adversarial": 15, "smoke": 10}


@pytest.fixture(scope="module")
def corpus() -> Corpus:
    return Corpus.load()


def test_datasets_match_the_version_store(corpus: Corpus) -> None:
    cases, today = load(list(SIZES)), date.today()
    assert Counter(name for name, _ in cases) == SIZES
    for _, case in cases:
        assert all(corpus.version_at(block_id, today) for block_id in case.gold + case.also), case.question
        text = " ".join(normalise(corpus.articles[block_id].versions[-1].text) for block_id in case.gold)
        assert all(normalise(fact) in text for fact in case.facts), case.question
        if case.block:
            versions = corpus.articles[case.block].versions
            assert any((v.norm, v.in_force) == (case.norm, case.in_force) for v in versions[:-1]), case.question
    shapes = {"golden": "gold", "versions": "block", "adversarial": "canary"}
    assert all(getattr(case, shapes[name]) for name, case in cases if name in shapes)
    assert not any(case.answerable for name, case in cases if name == "unanswerable")
    smoke = {case.model_dump_json() for name, case in cases if name == "smoke"}
    assert smoke <= {case.model_dump_json() for name, case in cases if name != "smoke"}


def answer(*citations: Citation, text: str = "La pena es de prisión de diez a quince años. [1]") -> Answer:
    return Answer(text=text, citations=list(citations), claims=1, dropped_claims=0, language="es", facts_date=None)


def observed(outcome: Answer | Refusal, retrieved: list[str]) -> Observed:
    grounded = 0.75 if isinstance(outcome, Answer) else None
    return Observed(outcome=outcome, retrieved=retrieved, seconds=1.0, groundedness=grounded)


async def test_gate_scores_each_metric(corpus: Corpus) -> None:
    homicide, murder_2014 = corpus.cite("a138"), corpus.cite("a139", date(2014, 5, 15))
    assert homicide and murder_2014
    then = Case(question="q5", block="a139", norm="BOE-A-1995-25444", in_force=date(1996, 5, 24))
    pairs = [
        (Case(question="q1", gold=["a138"]), observed(answer(homicide), ["a138", "a142"])),
        (Case(question="q2", gold=["a142"]), observed(answer(homicide), ["a1", "a2", "a3", "a4", "a5", "a142"])),
        (Case(question="q3", answerable=False), observed(Refusal(reason="out_of_scope"), [])),
        (Case(question="q4", canary="ZEBRA-7731"), observed(Refusal(reason="out_of_scope", detail="Zebra 7731."), [])),
        (then, observed(answer(murder_2014), ["a139"])),
        (then.model_copy(update={"question": "q6"}), observed(answer(corpus.cite("a139") or murder_2014), ["a139"])),
        (Case(question="q7", language="en"), observed(answer(homicide, text="The penalty is prison. [1]"), ["a138"])),
    ]
    found = await measure(pairs, [])
    assert found["recall_at_5"][:2] == found["citation_precision"][:2] == (0.5, 2)
    assert found["version_accuracy"] == (0.5, 2, ["q6"])
    assert found["correct_refusal"][0] == 1.0 and found["false_refusal"][:2] == (0.0, 5)
    assert found["canary_appearances"] == (1.0, 1, ["q4"])
    assert found["answer_language"][:2] == (1.0, 5) and found["groundedness"][:2] == (0.75, 5)
    assert report("header", pairs, found).startswith("### Juriscope evaluation: failed") and not gate(found)
    clean = {name: (float("max" not in rule), 2, list[str]()) for name, rule in THRESHOLDS.items()}
    assert gate(clean) and not gate(clean | {"errors": (1, 1, ["q8: ChatClientException"])})
    del clean["canary_appearances"]
    assert not gate(clean) and "canary_appearances: no case" in report("header", pairs, clean)


def test_only_in_stream_errors_are_retried() -> None:
    request = httpx2.Request("POST", "https://example.org")
    for cause, retried in [
        (APIError("rate limit", request, body=None), True),
        (APIStatusError("bad", response=httpx2.Response(400, request=request), body=None), False),
        (None, False),
    ]:
        error = ChatClientException("failed")
        error.__cause__ = cause
        assert throttled(error) is retried


def test_thresholds_bound_the_gate() -> None:
    assert passes("false_refusal", 0.05) and not passes("false_refusal", 0.06)
    assert passes("canary_appearances", 0.0) and not passes("canary_appearances", 1 / 15)
    assert passes("groundedness", 0.9) and not passes("recall_at_5", float("nan"))
    assert passes("answer_language", 0.0)
