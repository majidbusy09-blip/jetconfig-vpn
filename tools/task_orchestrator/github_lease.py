"""Deterministic lease records and CAS plans for GitHub-ref task ownership.

No network calls are made here. A trusted GitHub adapter must execute the
returned create-ref / compare-and-swap plan and verify every resulting ref SHA.
"""
from __future__ import annotations
import argparse, json, re
from datetime import datetime, timedelta, timezone
from typing import Any

LEASE_SCHEMA = 1
TASK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
AGENTS = {"chatgpt", "grok"}
MAX_LEASE_MINUTES = 240


class LeaseError(ValueError):
    pass


def _utc(value: str) -> datetime:
    if not isinstance(value, str):
        raise LeaseError("Lease timestamps must be ISO-8601 text.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LeaseError("Invalid ISO-8601 lease timestamp.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise LeaseError("Lease timestamps must include a timezone.")
    return parsed.astimezone(timezone.utc)


def lock_branch(task_id: str) -> str:
    if not isinstance(task_id, str) or not TASK_ID_RE.fullmatch(task_id):
        raise LeaseError("Invalid task_id.")
    return f"agent-locks/{task_id}"


def validate_lease(value: Any) -> dict[str, Any]:
    fields = {"schema_version", "task_id", "owner", "claim_id", "status", "claimed_at", "expires_at", "base_sha"}
    if not isinstance(value, dict) or set(value) != fields:
        raise LeaseError("Lease record must contain exactly the documented fields.")
    if isinstance(value["schema_version"], bool) or value["schema_version"] != LEASE_SCHEMA:
        raise LeaseError("Unsupported lease schema.")
    task_id = value["task_id"]
    if not isinstance(task_id, str) or not TASK_ID_RE.fullmatch(task_id):
        raise LeaseError("Invalid task_id.")
    if value["owner"] not in AGENTS:
        raise LeaseError("owner must be chatgpt or grok.")
    if not isinstance(value["claim_id"], str) or not re.fullmatch(r"[a-f0-9]{16,64}", value["claim_id"]):
        raise LeaseError("claim_id must be 16-64 lowercase hexadecimal characters.")
    if value["status"] not in {"active", "released"}:
        raise LeaseError("Invalid lease status.")
    claimed, expires = _utc(value["claimed_at"]), _utc(value["expires_at"])
    if expires <= claimed or expires - claimed > timedelta(minutes=MAX_LEASE_MINUTES):
        raise LeaseError("Lease duration must be positive and at most four hours.")
    base_sha = value["base_sha"]
    if not isinstance(base_sha, str) or not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", base_sha):
        raise LeaseError("base_sha must be a full Git object ID.")
    return {"schema_version": 1, "task_id": task_id, "owner": value["owner"],
            "claim_id": value["claim_id"], "status": value["status"],
            "claimed_at": claimed.isoformat().replace("+00:00", "Z"),
            "expires_at": expires.isoformat().replace("+00:00", "Z"), "base_sha": base_sha}


def make_lease(*, task_id: str, owner: str, claim_id: str, base_sha: str,
               now: str, duration_minutes: int = 60) -> dict[str, Any]:
    if isinstance(duration_minutes, bool) or not isinstance(duration_minutes, int) or not 1 <= duration_minutes <= MAX_LEASE_MINUTES:
        raise LeaseError("duration_minutes must be between 1 and 240.")
    claimed = _utc(now)
    record = {"schema_version": 1, "task_id": task_id, "owner": owner, "claim_id": claim_id,
              "status": "active", "claimed_at": claimed.isoformat().replace("+00:00", "Z"),
              "expires_at": (claimed + timedelta(minutes=duration_minutes)).isoformat().replace("+00:00", "Z"),
              "base_sha": base_sha}
    return validate_lease(record)


def transition_plan(current: dict[str, Any] | None, proposed: dict[str, Any],
                    *, observed_ref_sha: str | None, now: str) -> dict[str, Any]:
    next_record = validate_lease(proposed)
    if current is None:
        if observed_ref_sha is not None:
            raise LeaseError("Existing lock ref must be read and its lease inspected.")
        return {"operation": "create-lock-ref", "branch": lock_branch(next_record["task_id"]),
                "record": next_record, "expected_sha": None}
    prior = validate_lease(current)
    if prior["task_id"] != next_record["task_id"]:
        raise LeaseError("Task ID mismatch.")
    if prior["base_sha"] != next_record["base_sha"]:
        raise LeaseError("Task base SHA mismatch.")
    if observed_ref_sha is None or not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", observed_ref_sha):
        raise LeaseError("A full observed lock-ref SHA is required for compare-and-swap.")
    if prior["status"] == "active" and _utc(prior["expires_at"]) > _utc(now):
        raise LeaseError("Task is already leased; do not steal an unexpired lease.")
    if next_record["owner"] == prior["owner"] and next_record["claim_id"] == prior["claim_id"]:
        raise LeaseError("Renewal must use a fresh claim_id to avoid replay.")
    return {"operation": "compare-and-swap", "branch": lock_branch(next_record["task_id"]),
            "record": next_record, "expected_sha": observed_ref_sha}


def renew_plan(current: dict[str, Any], proposed: dict[str, Any], *,
               observed_ref_sha: str, owner: str, claim_id: str, now: str) -> dict[str, Any]:
    prior, next_record = validate_lease(current), validate_lease(proposed)
    moment = _utc(now)
    if prior["status"] != "active" or _utc(prior["expires_at"]) <= moment:
        raise LeaseError("Only an unexpired active lease can be renewed.")
    if prior["owner"] != owner or prior["claim_id"] != claim_id:
        raise LeaseError("Only the current lease owner may renew this claim.")
    if next_record["owner"] != owner or next_record["task_id"] != prior["task_id"]:
        raise LeaseError("Renewal owner or task ID mismatch.")
    if next_record["base_sha"] != prior["base_sha"]:
        raise LeaseError("Renewal cannot change the pinned task base SHA.")
    if next_record["claim_id"] == claim_id:
        raise LeaseError("Renewal requires a fresh claim_id to prevent replay.")
    if _utc(next_record["claimed_at"]) != moment:
        raise LeaseError("Renewal claimed_at must equal the supplied current time.")
    if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", observed_ref_sha):
        raise LeaseError("A full observed lock-ref SHA is required.")
    return {"operation": "compare-and-swap", "branch": lock_branch(prior["task_id"]),
            "record": next_record, "expected_sha": observed_ref_sha}


def release_plan(current: dict[str, Any], *, observed_ref_sha: str,
                 owner: str, claim_id: str, now: str) -> dict[str, Any]:
    prior = validate_lease(current)
    if prior["owner"] != owner or prior["claim_id"] != claim_id or prior["status"] != "active":
        raise LeaseError("Only the current lease owner may release this active claim.")
    _utc(now)
    if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", observed_ref_sha):
        raise LeaseError("A full observed lock-ref SHA is required.")
    return {"operation": "compare-and-swap", "branch": lock_branch(prior["task_id"]),
            "record": dict(prior, status="released"), "expected_sha": observed_ref_sha}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--owner", required=True, choices=sorted(AGENTS))
    parser.add_argument("--claim-id", required=True)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--now", required=True)
    parser.add_argument("--minutes", type=int, default=60)
    args = parser.parse_args()
    try:
        record = make_lease(task_id=args.task_id, owner=args.owner, claim_id=args.claim_id,
                            base_sha=args.base_sha, now=args.now, duration_minutes=args.minutes)
    except LeaseError as exc:
        parser.error(str(exc))
    print(json.dumps({"branch": lock_branch(args.task_id), "record": record,
                      "note": "Record only; authenticated GitHub adapter must create the lock ref atomically."}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
