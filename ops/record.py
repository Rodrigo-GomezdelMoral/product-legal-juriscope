import argparse
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

RUNS: dict[str, tuple[str, list[str]]] = {
    "s1": ("Reckless homicide, with the full articles", ["What is the penalty for reckless homicide?"]),
    "s2": ("Murder in May 2014 and today", ["¿Qué decía el artículo 139 sobre el asesinato en mayo de 2014?"]),
    "s3": ("Case-law question, refused", ["¿Qué ha dicho el Tribunal Supremo sobre la legítima defensa putativa?"]),
    "s4": (
        "Fraud: limitation and a follow-up",
        ["¿Cuándo prescribe un delito de estafa?", "¿Y si la estafa es agravada?"],
    ),
    "s5": ("Self-defence, asked in English", ["What does the Criminal Code say about self-defence?"]),
}


def ask(client: httpx.Client, conversation: str, question: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    block: dict[str, str] = {}
    start = time.monotonic()
    with client.stream("POST", f"/api/conversations/{conversation}/messages", json={"question": question}) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if line:
                key, _, value = line.partition(":")
                block[key] = value.strip()
                continue
            if "data" in block:
                at = round((time.monotonic() - start) * 1000)
                events.append({"event": block.get("event"), "data": json.loads(block["data"]), "at": at})
            block = {}
    return events


def anonymous(run: str, number: int, events: list[dict[str, Any]]) -> dict[str, Any]:
    if not events or events[-1]["event"] not in {"answer", "refusal"}:
        raise RuntimeError(f"{run} turn {number} ended without an answer or a refusal: {events[-1:]}")
    events[-1]["data"] |= {"conversation_id": run}
    events[-1]["data"]["turn"]["id"] = f"{run}-{number}"
    return {"question": events[-1]["data"]["turn"]["question"], "events": events}


def record(client: httpx.Client, run: str, out: Path) -> None:
    title, questions = RUNS[run]
    conversation, turns = "new", []
    try:
        for number, question in enumerate(questions, 1):
            events = ask(client, conversation, question)
            conversation = events[-1]["data"].get("conversation_id", conversation)
            turns.append(anonymous(run, number, events))
    finally:
        if conversation != "new":
            client.delete(f"/api/conversations/{conversation}").raise_for_status()
    meta = client.get("/api/meta").raise_for_status().json()
    recorded = datetime.now(UTC).date().isoformat()
    body = {"id": run, "title": title, "recorded": recorded, "meta": meta, "turns": turns}
    (out / f"{run}.json").write_text(json.dumps(body, ensure_ascii=False, indent=1) + "\n", "utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Record demo runs from a running Juriscope API.")
    parser.add_argument("--url", required=True)
    parser.add_argument("--out", type=Path, default=Path("web/fixtures"))
    parser.add_argument("runs", nargs="*", default=list(RUNS))
    args = parser.parse_args()
    name, _, value = os.environ.get("RECORD_AUTH_HEADER", "").partition(": ")
    with httpx.Client(base_url=args.url, headers={name: value} if value else {}, timeout=120) as client:
        for run in args.runs:
            record(client, run, args.out)


if __name__ == "__main__":
    main()
