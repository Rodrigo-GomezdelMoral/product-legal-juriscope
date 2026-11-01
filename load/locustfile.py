import json
import os
import random
import time
from pathlib import Path

from locust import HttpUser, LoadTestShape, between, task

SCENARIO, TOKEN = os.environ.get("LOAD_SCENARIO", "normal"), os.environ.get("LOAD_TOKEN", "")
GOLDEN = Path(__file__).parent.parent / "eval" / "datasets" / "golden.jsonl"
QUESTIONS = [json.loads(line)["question"] for line in GOLDEN.read_text("utf-8").splitlines() if line.strip()]
SHAPES = {"normal": (5, 180), "peak": (20, 120), "soak": (5, 600), "real": (3, 120)}
STRESS_STEP, STRESS_ERRORS, STRESS_SECONDS = 5, 0.05, 1200


class Lawyer(HttpUser):
    wait_time = between(5, 15)

    def on_start(self) -> None:
        self.client.headers["Authorization"] = f"Bearer {TOKEN}"

    @task
    def ask(self) -> None:
        body, path = {"question": random.choice(QUESTIONS)}, "/api/conversations/new/messages"
        with self.client.post(path, json=body, name="ask", catch_response=True) as response:
            lines = [line.removeprefix("data:") for line in response.text.splitlines() if line.startswith("data:")]
            outcome = next((json.loads(line) for line in lines if '"turn"' in line), None)
            if response.status_code != 200 or outcome is None:
                response.failure(f"status {response.status_code} without an answer or a refusal")
                return
        self.client.delete(f"/api/conversations/{outcome['conversation_id']}", name="delete")


class Shape(LoadTestShape):
    def tick(self) -> tuple[int, float] | None:
        elapsed = time.perf_counter() - self.start_time
        if SCENARIO == "stress":
            total = self.runner.stats.total if self.runner else None
            failing = total is not None and total.num_requests > 50 and total.fail_ratio > STRESS_ERRORS
            users = STRESS_STEP * (1 + int(elapsed // 60))
            return None if failing or elapsed > STRESS_SECONDS else (users, STRESS_STEP)
        users, seconds = SHAPES[SCENARIO]
        return (users, users) if elapsed < seconds else None
