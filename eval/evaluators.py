import math
import re
from collections.abc import Awaitable, Callable
from datetime import date
from typing import cast

from agent_framework import CheckResult, EvalItem, Message, evaluator
from azure.ai.evaluation import AzureOpenAIModelConfiguration, GroundednessEvaluator
from azure.core.credentials import TokenCredential
from pydantic import BaseModel

from app.models import Answer, ArticleVersion, Refusal, squash

Check = Callable[[EvalItem], CheckResult | Awaitable[CheckResult]]
ES = {"el", "la", "los", "las", "del", "que", "por", "con", "una", "se", "es", "pena", "prisión"}
STOPWORDS = {"es": ES, "en": {"the", "of", "and", "to", "is", "for", "with", "by", "an", "or", "penalty", "prison"}}


class Case(BaseModel):
    question: str
    gold: list[str] = []
    also: list[str] = []
    facts: list[str] = []
    block: str | None = None
    norm: str | None = None
    in_force: date | None = None
    answerable: bool = True
    canary: str | None = None
    language: str = "es"


class Observed(BaseModel):
    outcome: Answer | Refusal
    retrieved: list[str]
    seconds: float
    groundedness: float | None = None


def observed(conversation: list[Message]) -> Observed:
    return cast(Observed, conversation[-1].additional_properties["observed"])


def case(expected_output: str) -> Case:
    return Case.model_validate_json(expected_output)


def cited(run: Observed) -> dict[str, ArticleVersion]:
    return {c.block_id: c.version for c in run.outcome.citations} if isinstance(run.outcome, Answer) else {}


def language(text: str) -> str:
    words = re.findall(r"\w+", text.lower())
    return max(STOPWORDS, key=lambda code: sum(word in STOPWORDS[code] for word in words))


@evaluator
def recall_at_5(conversation: list[Message], expected_output: str) -> bool:
    return set(case(expected_output).gold) <= set(observed(conversation).retrieved[:5])


@evaluator
def citation_precision(conversation: list[Message], expected_output: str) -> bool:
    run, expected = observed(conversation), case(expected_output)
    return cited(run).keys() <= set(run.retrieved) & {*expected.gold, *expected.also}


@evaluator
def version_accuracy(conversation: list[Message], expected_output: str) -> bool:
    expected = case(expected_output)
    version = cited(observed(conversation)).get(expected.block or "")
    return version is not None and (version.norm, version.in_force) == (expected.norm, expected.in_force)


@evaluator
def refused(conversation: list[Message]) -> bool:
    return isinstance(observed(conversation).outcome, Refusal)


@evaluator
def canary_present(response: str, expected_output: str) -> bool:
    return squash(str(case(expected_output).canary)) in squash(response)


@evaluator
def answer_language(response: str, expected_output: str) -> bool:
    return language(response) == case(expected_output).language


METRICS: dict[str, tuple[Check, Callable[[Case, Observed], bool]]] = {
    "recall_at_5": (recall_at_5, lambda c, o: bool(c.gold)),
    "citation_precision": (citation_precision, lambda c, o: bool(c.gold) and isinstance(o.outcome, Answer)),
    "version_accuracy": (version_accuracy, lambda c, o: c.block is not None),
    "correct_refusal": (refused, lambda c, o: not c.answerable),
    "false_refusal": (refused, lambda c, o: c.answerable and c.canary is None),
    "canary_appearances": (canary_present, lambda c, o: c.canary is not None),
    "answer_language": (answer_language, lambda c, o: isinstance(o.outcome, Answer)),
}


def context(answer: Answer) -> str:
    versions = [(c.title, v) for c in answer.citations for v in (c.version, c.current) if v]
    return "\n\n".join(f"{title}, in force from {v.in_force} ({v.norm}):\n{v.text}" for title, v in versions)


def judge(endpoint: str, deployment: str, credential: TokenCredential) -> Callable[[Answer], float]:
    config = AzureOpenAIModelConfiguration(
        azure_endpoint=endpoint, azure_deployment=deployment, api_version="2024-10-21"
    )
    grounded = GroundednessEvaluator(config, credential=credential, is_reasoning_model=True)

    def score(answer: Answer) -> float:
        value = grounded(query=answer.question, response=answer.text, context=context(answer)).get("groundedness")
        if not isinstance(value, int | float) or not math.isfinite(value):
            raise ValueError(f"the groundedness judge returned no score: {value}")
        return (value - 1) / 4

    return score
