import ast
import io
import ipaddress
import re
import subprocess
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXCLUDED = ("docs/", "data/", "eval/datasets/", "web/fixtures/", "web/public/")
LOCK_FILES = ("package-lock.json",)
APP_DIRS = ("app/", "ops/", "eval/", "load/")
REQUIREMENTS = ("requirements.txt", "requirements-dev.txt")
LIMITS = {"files": 90, "Python": 1400, "tests": 700, "Bicep": 490, "TypeScript": 799, "comments": 5}
MAX_FUNCTION_LINES = 35
BLIND = {"Exception", "BaseException"}
COMMENT_PREFIXES = {
    **dict.fromkeys((".bicep", ".bicepparam", ".ts", ".tsx"), ("//", "/*", "{/*")),
    **dict.fromkeys((".yml", ".yaml", "Dockerfile", "Makefile"), ("#",)),
}
ENDPOINTS = (
    r"services\.ai\.azure\.com|openai\.azure\.com|cognitiveservices\.azure\.com|search\.windows\.net|"
    r"documents\.azure\.com|vault\.azure\.net|blob\.core\.windows\.net|azurecr\.io|azurecontainerapps\.io"
)
IDENTIFIERS = {
    "GUID": re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE),
    "e-mail address": re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}"),
    "endpoint host": re.compile(rf"[A-Za-z0-9-]+\.(?:{ENDPOINTS})", re.IGNORECASE),
    "tenant domain": re.compile(r"[\w-]+\.onmicrosoft\.com", re.IGNORECASE),
    "local user path": re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+\w", re.IGNORECASE),
}
IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
PINNED_ACTION = re.compile(r"uses:\s*[\w.-]+/[\w./-]+@(?:v\d+(?:\.\d+)*|[0-9a-f]{40})\s*$")


def listed_files() -> list[str]:
    command = ["git", "ls-files", "--cached", "--others", "--exclude-standard"]
    names = subprocess.run(command, capture_output=True, text=True, check=True, cwd=ROOT).stdout.splitlines()
    return [name for name in names if (ROOT / name).is_file() and "node_modules/" not in name]


def budgeted_files() -> list[str]:
    return [name for name in listed_files() if not name.startswith(EXCLUDED) and Path(name).name not in LOCK_FILES]


def text_lines(name: str) -> list[str]:
    return (ROOT / name).read_text(encoding="utf-8").splitlines()


def non_blank_lines(names: list[str]) -> int:
    return sum(1 for name in names for line in text_lines(name) if line.strip())


def comment_count(names: list[str]) -> int:
    python = ((ROOT / name).read_text(encoding="utf-8") for name in names if name.endswith(".py"))
    tokens = (token for source in python for token in tokenize.generate_tokens(io.StringIO(source).readline))
    count = sum(1 for token in tokens if token.type == tokenize.COMMENT)
    for name in names:
        prefixes = next((value for suffix, value in COMMENT_PREFIXES.items() if name.endswith(suffix)), None)
        if prefixes:
            count += sum(1 for line in text_lines(name) if line.strip().startswith(prefixes))
    return count


def budget_counts() -> dict[str, int]:
    files = budgeted_files()
    python = [name for name in files if name.endswith(".py")]
    return {
        "files": len(files),
        "Python": non_blank_lines([name for name in python if name.startswith(APP_DIRS)]),
        "tests": non_blank_lines([name for name in python if name.startswith("tests/")]),
        "Bicep": non_blank_lines([name for name in files if name.endswith((".bicep", ".bicepparam"))]),
        "TypeScript": non_blank_lines([name for name in files if name.endswith((".ts", ".tsx"))]),
        "comments": comment_count(files),
    }


def is_public_ip(text: str) -> bool:
    try:
        return ipaddress.ip_address(text).is_global
    except ValueError:
        return False


def test_size_budget() -> None:
    over = {name: count for name, count in budget_counts().items() if count > LIMITS[name]}
    assert not over, f"over budget: {over}"


def test_python_craft() -> None:
    for name in (name for name in budgeted_files() if name.endswith(".py")):
        for node in ast.walk(ast.parse((ROOT / name).read_text(encoding="utf-8"))):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                length = (node.end_lineno or node.lineno) - node.lineno + 1
                assert length <= MAX_FUNCTION_LINES, f"{name}:{node.name} is {length} lines"
            if isinstance(node, ast.ExceptHandler):
                blind = node.type is None or (isinstance(node.type, ast.Name) and node.type.id in BLIND)
                assert not blind, f"{name}:{node.lineno} catches everything"


def test_no_identifiers() -> None:
    found: list[str] = []
    for name in listed_files():
        raw = (ROOT / name).read_bytes()
        try:
            text = "" if b"\0" in raw else raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        found += [f"{name}: {kind}" for kind, pattern in IDENTIFIERS.items() if pattern.search(text)]
        found += [f"{name}: public IP address" for match in IPV4.findall(text) if is_public_ip(match)]
    assert not found, found


def test_supply_chain_is_pinned() -> None:
    pins = [line for name in REQUIREMENTS for line in text_lines(name)]
    for pin in (pin for pin in pins if pin and not pin.startswith("-r")):
        assert "==" in pin, f"unpinned dependency {pin}"
        assert not pin.startswith("agent-framework=="), "the agent-framework metapackage is not allowed"
    for workflow in (ROOT / ".github" / "workflows").glob("*.yml"):
        for line in workflow.read_text(encoding="utf-8").splitlines():
            if line.strip().removeprefix("- ").startswith("uses:"):
                assert PINNED_ACTION.search(line), f"{workflow.name}: action not pinned to a major or a commit SHA"
