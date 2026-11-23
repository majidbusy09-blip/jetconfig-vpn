"""Provider-neutral validation for GitHub Issue based agent tasks."""
from __future__ import annotations
import argparse, json, re, sys
from typing import Any

MARKER = "<!-- jet-agent-task:v1 -->"
TASK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
CAPABILITIES = {"implementation", "bug_fix", "refactor", "documentation", "investigation"}
RISKS = {"low", "medium", "high"}
AGENTS = {"any", "chatgpt", "grok"}
PROFILES = {"python-tooling-tests", "flutter-tests", "flutter-analysis", "lexical-memory-audit"}
MAX_BODY, MAX_GOAL, MAX_ITEMS = 32_000, 8_000, 50
PROTECTED_PARTS = {".git", ".agent", ".secrets", "secrets", "credentials", "keystore", "signing", "release-assets"}


class GitHubTaskError(ValueError):
    """A GitHub task issue failed closed validation."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise GitHubTaskError("Duplicate JSON keys are not allowed.")
        result[key] = value
    return result


def _text(value: Any, name: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit or "\x00" in value:
        raise GitHubTaskError(f"{name} must be non-empty text of at most {limit} characters.")
    return value.strip()


def _paths(value: Any, name: str, *, required: bool) -> list[str]:
    if not isinstance(value, list) or len(value) > MAX_ITEMS or (required and not value):
        raise GitHubTaskError(f"{name} must be {'a non-empty ' if required else 'an '}array of at most {MAX_ITEMS} paths.")
    result = []
    for raw in value:
        path = _text(raw, f"{name}[]", 256)
        if path.startswith("/") or "\\" in path or re.match(r"^[A-Za-z]:", path):
            raise GitHubTaskError(f"{name} contains a non-repository-relative path.")
        parts = path.split("/")
        if any(part in {"", ".", ".."} for part in parts):
            raise GitHubTaskError(f"{name} contains an unsafe path segment.")
        if any(part.lower() in PROTECTED_PARTS for part in parts) or path.startswith(".github/workflows/"):
            raise GitHubTaskError(f"{name} targets a protected path.")
        if path in result:
            raise GitHubTaskError(f"{name} contains duplicate entries.")
        result.append(path)
    return result


def validate_task_payload(value: Any) -> dict[str, Any]:
    required = {"schema_version", "task_id", "goal", "capability", "risk", "assigned_agent", "allow", "exclude", "scope_reason", "verification_profiles"}
    if not isinstance(value, dict) or set(value) != required:
        raise GitHubTaskError("Task payload must contain exactly the documented fields.")
    if isinstance(value["schema_version"], bool) or value["schema_version"] != 1:
        raise GitHubTaskError("Unsupported GitHub task schema_version.")
    task_id = _text(value["task_id"], "task_id", 64)
    if not TASK_ID_RE.fullmatch(task_id):
        raise GitHubTaskError("task_id must be 3-64 lowercase letters, digits, or hyphens.")
    for key, allowed in (("capability", CAPABILITIES), ("risk", RISKS), ("assigned_agent", AGENTS)):
        if not isinstance(value[key], str) or value[key] not in allowed:
            raise GitHubTaskError(f"Unsupported {key}.")
    profiles = value["verification_profiles"]
    if not isinstance(profiles, list) or not profiles or len(profiles) > 12 or not all(isinstance(x, str) and x in PROFILES for x in profiles):
        raise GitHubTaskError("verification_profiles must contain only supported fixed profiles.")
    if len(set(profiles)) != len(profiles):
        raise GitHubTaskError("verification_profiles must not contain duplicates.")
    return {
        "schema_version": 1, "task_id": task_id, "goal": _text(value["goal"], "goal", MAX_GOAL),
        "capability": value["capability"], "risk": value["risk"], "assigned_agent": value["assigned_agent"],
        "allow": _paths(value["allow"], "allow", required=True),
        "exclude": _paths(value["exclude"], "exclude", required=False),
        "scope_reason": _text(value["scope_reason"], "scope_reason", 2_000),
        "verification_profiles": profiles,
    }


def validate_issue_body(body: str) -> dict[str, Any]:
    if not isinstance(body, str) or len(body.encode("utf-8")) > MAX_BODY:
        raise GitHubTaskError("Issue body is missing or exceeds the configured size limit.")
    if body.count(MARKER) != 1:
        raise GitHubTaskError("Issue body must contain exactly one GitHub task marker.")
    marked = body.split(MARKER, 1)[1]
    fence = re.escape(chr(96) * 3)
    blocks = re.findall(fence + r"json\s*\n(.*?)\n" + fence, marked, flags=re.DOTALL | re.IGNORECASE)
    if len(blocks) != 1:
        raise GitHubTaskError("Issue body must contain exactly one fenced JSON task payload after the marker.")
    try:
        payload = json.loads(blocks[0], object_pairs_hook=_unique_object)
    except (json.JSONDecodeError, GitHubTaskError) as exc:
        raise GitHubTaskError("Issue task payload is not valid unique-key JSON.") from exc
    return validate_task_payload(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body-file", required=True, help="UTF-8 file containing the GitHub Issue body.")
    args = parser.parse_args(argv)
    try:
        with open(args.body_file, "r", encoding="utf-8") as handle:
            result = validate_issue_body(handle.read())
    except (OSError, UnicodeError, GitHubTaskError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
