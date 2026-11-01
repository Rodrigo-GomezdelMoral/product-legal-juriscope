import asyncio
import re
import statistics
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import yaml
from agent_framework import EvalItem, InMemoryHistoryProvider, LocalEvaluator, Message
from agent_framework.exceptions import AgentFrameworkException
from azure.core.credentials import TokenCredential
from azure.core.credentials_async import AsyncTokenCredential
from azure.core.exceptions import AzureError
from azure.identity import DefaultAzureCredential as JudgeCredential
from azure.identity.aio import DefaultAzureCredential
from openai import APIConnectionError, APITimeoutError

from app.agents import EFFORT, chat_client
from app.config import SharedBase
from app.corpus import Corpus
from app.models import Answer, Refusal
from app.retrieval import Chunk, SearchRetriever
from app.workflow import Juriscope, throttled
from eval.evaluators import METRICS, Case, Observed, judge

ROOT = Path(__file__).resolve().parent
FULL = ["golden", "versions", "unanswerable", "adversarial"]
THRESHOLDS: dict[str, dict[str, float]] = yaml.safe_load((ROOT / "thresholds.yaml").read_text("utf-8"))
CONCURRENCY, PAUSES, LOW_GROUNDEDNESS = 4, (20, 40, 80), 0.75
HOST = re.compile(r"[\w-]+(?:\.[\w-]+)*\.(?:com|net|io)\b\S*")
Metric = tuple[float, int, list[str]]


def retried(error: BaseException) -> bool:
    cause = error.__cause__
    return throttled(error) or (isinstance(cause, APIConnectionError) and not isinstance(cause, APITimeoutError))


def load(names: list[str]) -> list[tuple[str, Case]]:
    lines = [
        (name, line) for name in names for line in (ROOT / "datasets" / f"{name}.jsonl").read_text("utf-8").split("\n")
    ]
    return [(name, Case.model_validate_json(line)) for name, line in lines if line.strip()]


class Runner:
    def __init__(self, settings: SharedBase, credential: AsyncTokenCredential, judging: TokenCredential) -> None:
        self.corpus, self.model, self.gate = Corpus.load(), settings.chat_model, asyncio.Semaphore(CONCURRENCY)
        self.client = chat_client(settings, credential)
        self.retriever = SearchRetriever(settings.search_endpoint, settings.search_index, credential)
        self.score = judge(settings.foundry_account_endpoint, settings.chat_model, judging)

    async def observe(self, case: Case) -> Observed:
        chunks: list[Chunk] = []

        async def search(queries: list[str]) -> list[Chunk]:
            chunks.extend(found := await self.retriever.search(queries))
            return found

        started, history = time.time(), InMemoryHistoryProvider()
        *_, outcome = [
            e async for e in Juriscope(self.client, search, self.corpus, history, self.model).ask("eval", case.question)
        ]
        assert isinstance(outcome, Answer | Refusal)
        run = Observed(outcome=outcome, retrieved=[], seconds=round(time.time() - started, 2))
        run.retrieved = list(dict.fromkeys(b for chunk in chunks for b in self.corpus.locate(chunk.content)))
        run.groundedness = await asyncio.to_thread(self.score, outcome) if isinstance(outcome, Answer) else None
        return run

    async def attempt(self, case: Case, pauses: tuple[int, ...] = PAUSES) -> Observed | str:
        async with self.gate:
            try:
                return await self.observe(case)
            except (AgentFrameworkException, AzureError, ValueError, RuntimeError) as error:
                if not (pauses and retried(error)):
                    detail = HOST.sub("<host>", " ".join(str(error).split()))[:200]
                    return f"{case.question}: {type(error).__name__}: {detail}"
                print(f"{type(error.__cause__).__name__}, retry in {pauses[0]} s: {case.question}", file=sys.stderr)
        await asyncio.sleep(pauses[0])
        return await self.attempt(case, pauses[1:])


def item(case: Case, run: Observed) -> EvalItem:
    text = run.outcome.text if isinstance(run.outcome, Answer) else f"{run.outcome.reason}: {run.outcome.scope}"
    reply = Message("assistant", [text], additional_properties={"observed": run})
    return EvalItem([Message("user", [case.question]), reply], expected_output=case.model_dump_json())


async def measure(pairs: list[tuple[Case, Observed]], errors: list[str]) -> dict[str, Metric]:
    found: dict[str, Metric] = {"errors": (len(errors), len(errors), errors)}
    for name, (check, applies) in METRICS.items():
        if items := [item(c, o) for c, o in pairs if applies(c, o)]:
            result = await LocalEvaluator(check).evaluate(items, eval_name=name)
            bad = [r.input_text or "" for r in result.items if r.is_passed == ("max" in THRESHOLDS.get(name, {}))]
            found[name] = (result.passed / result.total, result.total, bad)
    if scores := [(c.question, o.groundedness) for c, o in pairs if o.groundedness is not None]:
        low = [question for question, score in scores if score < LOW_GROUNDEDNESS]
        found["groundedness"] = (statistics.fmean(score for _, score in scores), len(scores), low)
    return found


def passes(name: str, value: float) -> bool:
    rule = THRESHOLDS.get(name, {})
    return rule.get("min", value) <= value <= rule.get("max", value)


def gate(found: dict[str, Metric]) -> bool:
    return all(name in found and passes(name, found[name][0]) for name in THRESHOLDS)


def report(header: str, pairs: list[tuple[Case, Observed]], found: dict[str, Metric]) -> str:
    seconds = sorted(o.seconds for _, o in pairs) or [0.0]
    cost = statistics.median([o.outcome.cost_eur for _, o in pairs if isinstance(o.outcome, Answer)] or [0.0])
    lines = [f"### Juriscope evaluation: {'passed' if gate(found) else 'failed'}", "", header, ""]
    lines += ["| Metric | Value | Cases | Threshold | Pass |", "|---|---|---|---|---|"]
    for name, (value, total, _) in found.items():
        rule = " ".join(f"{key} {limit}" for key, limit in THRESHOLDS.get(name, {}).items())
        lines.append(f"| {name} | {value:.3f} | {total} | {rule} | {'✓✗'[not passes(name, value)] if rule else ''} |")
    p50, p95 = statistics.median(seconds), seconds[max(round(0.95 * len(seconds)) - 1, 0)]
    lines += ["", f"Seconds per question: p50 {p50:.1f}, p95 {p95:.1f}. Median cost of an answer: {cost:.4f} €.", ""]
    lines += [f"- {name}: no case to measure" for name in THRESHOLDS if name not in found]
    return "\n".join(lines + [f"- {name}: {text}" for name, (_, _, bad) in found.items() for text in bad]) + "\n"


async def main(names: list[str]) -> tuple[bool, str]:
    settings, cases = SharedBase(), load(names)
    with JudgeCredential() as judging:
        async with DefaultAzureCredential() as credential:
            runner = Runner(settings, credential, judging)
            runs = await asyncio.gather(*(runner.attempt(case) for _, case in cases))
            await runner.retriever.close()
    pairs = [(case, run) for (_, case), run in zip(cases, runs, strict=True) if isinstance(run, Observed)]
    found = await measure(pairs, [run for run in runs if isinstance(run, str)])
    sizes = ", ".join(f"{name} {count}" for name, count in Counter(name for name, _ in cases).items())
    setup = f"`{settings.chat_model}`, reasoning effort `{EFFORT}`, index `{settings.search_index}`"
    return gate(found), report(f"{datetime.now(UTC):%Y-%m-%d %H:%M} UTC · {sizes} · {setup}", pairs, found)


if __name__ == "__main__":
    passed, text = asyncio.run(main(sys.argv[1:] or FULL))
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "report.md").write_text(text, "utf-8")
    print(text)
    raise SystemExit(0 if passed else 1)
