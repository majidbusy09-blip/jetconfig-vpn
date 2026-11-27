"""Read-only task PR guard. Runs trusted-main code; never executes PR code."""
from __future__ import annotations
import argparse, base64, hashlib, json, os, re, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from .agent_contract import ContractValidationError, _path, _path_matches
from .github_issue_intake import (
    TASK_LABEL, IntakeError, load_project_configuration, validate_task_project_binding,
)
from .github_lease import LeaseError, lock_branch, validate_lease
from .project_namespace import ProjectNamespaceError, lease_record_path
from .github_task_protocol import GitHubTaskError, validate_issue_body

PR_MARKERS = {1: "<!-- jet-agent-pr:v1 -->", 2: "<!-- jet-agent-pr:v2 -->"}
MARKER = PR_MARKERS[1]
PROJECT_BINDING_FIELDS = {"project_id", "repository_id", "repository_full_name", "default_branch", "manifest_schema_version", "manifest_sha256"}
DIGEST_RE = re.compile(r"^[a-f0-9]{64}$")
AGENTS = {"chatgpt", "grok"}
CLAIM_RE = re.compile(r"^[a-f0-9]{16,64}$")
SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
REPO_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?/[A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?$")


class GuardError(ValueError):
    pass


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise GuardError("Duplicate PR envelope JSON key.")
        result[key] = value
    return result


def parse_pr_envelope(body):
    if not isinstance(body, str):
        return None
    found = [(version, marker) for version, marker in PR_MARKERS.items() if marker in body]
    if not found:
        return None
    if len(found) != 1 or body.count(found[0][1]) != 1:
        raise GuardError("Exactly one versioned PR marker is required.")
    marker_version, marker = found[0]
    tail = body.split(marker, 1)[1].strip()
    match = re.fullmatch(r"\x60\x60\x60json\s*(\{.*\})\s*\x60\x60\x60", tail, re.DOTALL)
    if not match:
        raise GuardError("Expected one fenced JSON object after PR marker.")
    try:
        value = json.loads(match.group(1), object_pairs_hook=_unique)
    except (json.JSONDecodeError, GuardError) as exc:
        raise GuardError("Invalid PR envelope JSON.") from exc
    common = {"schema_version", "task_issue", "owner", "claim_id"}
    expected = common if marker_version == 1 else common | {
        "issue_body_sha256", "project_binding", "base_sha",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise GuardError("PR envelope fields are invalid.")
    if isinstance(value["schema_version"], bool) or value["schema_version"] != marker_version:
        raise GuardError("PR marker and envelope schema version do not match.")
    if isinstance(value["task_issue"], bool) or not isinstance(value["task_issue"], int) or value["task_issue"] < 1:
        raise GuardError("task_issue must be a positive Issue number.")
    if not isinstance(value["owner"], str) or value["owner"] not in {"chatgpt", "grok"}:
        raise GuardError("owner must be chatgpt or grok.")
    if not isinstance(value["claim_id"], str) or not CLAIM_RE.fullmatch(value["claim_id"]):
        raise GuardError("claim_id format is invalid.")
    if marker_version == 2:
        if not isinstance(value["issue_body_sha256"], str) or not DIGEST_RE.fullmatch(value["issue_body_sha256"]):
            raise GuardError("v2 PR envelope Issue-body digest is invalid.")
        if not isinstance(value["base_sha"], str) or not SHA_RE.fullmatch(value["base_sha"]):
            raise GuardError("v2 PR envelope pinned base SHA is invalid.")
        binding = value["project_binding"]
        if not isinstance(binding, dict) or set(binding) != PROJECT_BINDING_FIELDS:
            raise GuardError("v2 PR envelope project binding is malformed.")
    return value


def api_get(repository, path, token):
    if not REPO_RE.fullmatch(repository) or not token:
        raise GuardError("Repository identity or read-only token is missing.")
    request = urllib.request.Request(
        "https://api.github.com/repos/" + repository + path,
        headers={"Accept": "application/vnd.github+json",
                 "Authorization": "Bearer " + token,
                 "X-GitHub-Api-Version": "2022-11-28",
                 "User-Agent": "JET-VPN-Agent-PR-Guard"},
        method="GET")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read(4_000_001)
    except urllib.error.HTTPError as exc:
        raise GuardError("GitHub read API returned HTTP " + str(exc.code) + ".") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise GuardError("GitHub read API request failed.") from exc
    if len(raw) > 4_000_000:
        raise GuardError("GitHub API response exceeded size limit.")
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GuardError("GitHub API returned invalid JSON.") from exc


def read_lease(repository, task_id, token, project_binding=None):
    try:
        branch = lock_branch(task_id, project_binding)
        path = lease_record_path(task_id, project_binding)
    except (LeaseError, ProjectNamespaceError) as exc:
        raise GuardError("Task project namespace is invalid.") from exc
    ref = api_get(repository, "/git/ref/heads/" + urllib.parse.quote(branch, safe="/-"), token)
    try:
        lock_sha = ref["object"]["sha"]
        lock_type = ref["object"]["type"]
    except (TypeError, KeyError) as exc:
        raise GuardError("Task lock ref is malformed.") from exc
    if lock_type != "commit" or not isinstance(lock_sha, str) or not SHA_RE.fullmatch(lock_sha):
        raise GuardError("Task lock ref must point to a full commit SHA.")
    query = urllib.parse.urlencode({"ref": lock_sha})
    item = api_get(repository, "/contents/" + urllib.parse.quote(path, safe="/.") + "?" + query, token)
    if not isinstance(item, dict) or item.get("encoding") != "base64" or not isinstance(item.get("content"), str):
        raise GuardError("Lease content response is malformed.")
    try:
        record = validate_lease(json.loads(base64.b64decode("".join(item["content"].split()), validate=True).decode("utf-8")))
        if record.get("project_binding") != project_binding:
            raise GuardError("Lease project identity differs from the validated task binding.")
        return record
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError, LeaseError) as exc:
        raise GuardError("Lease record is invalid.") from exc


def changed_files(repository, number, token):
    result = []
    for page in range(1, 11):
        query = urllib.parse.urlencode({"per_page": 100, "page": page})
        batch = api_get(repository, "/pulls/" + str(number) + "/files?" + query, token)
        if not isinstance(batch, list):
            raise GuardError("Changed-file response is malformed.")
        result.extend(batch)
        if len(result) > 1000:
            raise GuardError("PR exceeds the 1000-file guard limit.")
        if len(batch) < 100:
            return result
    raise GuardError("Changed-file pagination exceeded the guard limit.")


def validate_paths(files, allow, exclude):
    if not isinstance(files, list) or not files:
        raise GuardError("Agent PR must contain at least one changed file.")
    if len(files) > 100:
        raise GuardError("Agent PR exceeds the 100-file contract limit.")
    paths = []
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get("filename"), str):
            raise GuardError("Changed-file entry is malformed.")
        if item.get("status") not in {"added", "modified", "removed", "renamed"}:
            raise GuardError("Unsupported changed-file status.")
        candidates = [item["filename"]]
        if item.get("status") == "renamed":
            old = item.get("previous_filename")
            if not isinstance(old, str):
                raise GuardError("Renamed file is missing its old path.")
            candidates.append(old)
        for raw in candidates:
            try:
                path = _path(raw, "changed path")
            except ContractValidationError as exc:
                raise GuardError(str(exc)) from exc
            if any(_path_matches(path, pattern) for pattern in exclude):
                raise GuardError("Changed path is explicitly excluded: " + path)
            if not any(_path_matches(path, pattern) for pattern in allow):
                raise GuardError("Changed path is outside the task allowlist: " + path)
            paths.append(path)
    if len(paths) != len(set(paths)):
        raise GuardError("Duplicate changed paths are not accepted.")
    return paths


# Ordinary PRs are intentionally limited to application/documentation content.
# These roots contain CI policy, executable CI/release helpers, or project-memory
# producers/consumers. Changes there must use the task-scoped agent path.
PROTECTED_ORDINARY_PR_ROOTS = (".github", "tools", "scripts")
PROTECTED_ORDINARY_PR_EXACT = {
    "CODEOWNERS",
    "docs/CODEOWNERS",
    "gradlew",
    "gradlew.bat",
    "analysis_options.yaml",
    "build.gradle",
    "build.gradle.kts",
    "settings.gradle",
    "settings.gradle.kts",
    "gradle.properties",
    "pubspec.yaml",
    "pubspec.lock",
    "android/build.gradle",
    "android/build.gradle.kts",
    "android/settings.gradle",
    "android/settings.gradle.kts",
    "android/gradle.properties",
    "android/gradlew",
    "android/gradlew.bat",
    "android/gradle/wrapper/gradle-wrapper.properties",
    "android/app/proguard-rules.pro",
    "android/app/build.gradle",
    "android/app/build.gradle.kts",
}


def is_protected_ordinary_pr_path(path):
    """Return true for policy, CI, release, and build-control paths."""
    if not isinstance(path, str) or not path:
        return True
    if path in PROTECTED_ORDINARY_PR_EXACT:
        return True
    return any(path == root or path.startswith(root + "/")
               for root in PROTECTED_ORDINARY_PR_ROOTS)


def validate_non_agent_pr(event, *, token, repository):
    """Allow ordinary PRs only when they do not touch protected automation paths."""
    if not isinstance(event, dict) or event.get("action") not in {"opened", "synchronize", "reopened", "ready_for_review"}:
        raise GuardError("Pull request event is malformed or unsupported.")
    pr = event.get("pull_request")
    if not isinstance(pr, dict) or pr.get("state") != "open":
        raise GuardError("Pull request event is missing an open PR.")
    base = pr.get("base")
    if not isinstance(base, dict) or base.get("ref") != "main":
        raise GuardError("Pull request must target main.")
    if not REPO_RE.fullmatch(repository):
        raise GuardError("GITHUB_REPOSITORY is invalid.")
    event_repository = event.get("repository")
    if not isinstance(event_repository, dict) or event_repository.get("full_name") != repository:
        raise GuardError("Event repository mismatch.")
    live_repository = api_get(repository, "", token)
    for key in ("id", "full_name", "html_url", "default_branch"):
        if event_repository.get(key) != live_repository.get(key):
            raise GuardError("Event repository identity differs from live GitHub metadata.")
    base_repo = base.get("repo")
    if not isinstance(base_repo, dict):
        raise GuardError("PR base repository metadata is missing.")
    for key in ("id", "full_name", "html_url", "default_branch"):
        if base_repo.get(key) != live_repository.get(key):
            raise GuardError("PR base repository identity mismatch: " + key + ".")
    number = pr.get("number")
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise GuardError("PR number is invalid.")
    files = changed_files(repository, number, token)
    if not isinstance(files, list) or not files or len(files) > 1000:
        raise GuardError("Ordinary PR changed-file response is empty or exceeds the guard limit.")
    accepted = []
    for item in files:
        if not isinstance(item, dict) or item.get("status") not in {"added", "modified", "removed", "renamed"}:
            raise GuardError("Ordinary PR changed-file entry is malformed or unsupported.")
        filename = item.get("filename")
        if not isinstance(filename, str):
            raise GuardError("Ordinary PR changed-file path is missing.")
        candidates = [filename]
        if item["status"] == "renamed":
            previous = item.get("previous_filename")
            if not isinstance(previous, str):
                raise GuardError("Renamed ordinary PR file is missing its previous path.")
            candidates.append(previous)
        for raw in candidates:
            try:
                path = _path(raw, "changed path")
            except ContractValidationError as exc:
                raise GuardError(str(exc)) from exc
            if is_protected_ordinary_pr_path(path):
                raise GuardError("Ordinary PR cannot modify protected automation/build path: " + path)
            accepted.append(path)
    return {"status": "not-agent-pr", "message": "Ordinary PR changed paths contain no protected automation files.",
            "pr_number": number, "changed_paths": accepted, "file_count": len(accepted)}


def validate_agent_pr(event, *, token, repository, now=None):
    if not isinstance(event, dict) or event.get("action") not in {"opened", "synchronize", "reopened", "ready_for_review"} or not isinstance(event.get("pull_request"), dict):
        raise GuardError("Pull request event is malformed or unsupported.")
    pr = event["pull_request"]
    envelope = parse_pr_envelope(pr.get("body"))
    if envelope is None:
        return validate_non_agent_pr(event, token=token, repository=repository)
    if not REPO_RE.fullmatch(repository):
        raise GuardError("GITHUB_REPOSITORY is invalid.")
    if not isinstance(event.get("repository"), dict) or event["repository"].get("full_name") != repository:
        raise GuardError("Event repository mismatch.")
    event_repository = event["repository"]
    live_repository = api_get(repository, "", token)
    for key in ("id", "full_name", "html_url", "default_branch"):
        if event_repository.get(key) != live_repository.get(key):
            raise GuardError("Event repository identity differs from live GitHub metadata.")
    base, head = pr.get("base"), pr.get("head")
    if not isinstance(base, dict) or not isinstance(head, dict) or base.get("ref") != "main" or pr.get("state") != "open":
        raise GuardError("Agent PR must be open and target main.")
    if not isinstance(base.get("repo"), dict) or not isinstance(head.get("repo"), dict):
        raise GuardError("PR base/head repository metadata is missing.")
    for role, repo_data in (("base", base["repo"]), ("head", head["repo"])):
        for key in ("id", "full_name", "html_url", "default_branch"):
            if repo_data.get(key) != live_repository.get(key):
                raise GuardError("PR " + role + " repository identity mismatch: " + key + ".")
    base_sha, head_sha = base.get("sha"), head.get("sha")
    if not isinstance(base_sha, str) or not SHA_RE.fullmatch(base_sha) or not isinstance(head_sha, str) or not SHA_RE.fullmatch(head_sha):
        raise GuardError("PR base/head SHA is invalid.")
    number = pr.get("number")
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise GuardError("PR number is invalid.")

    issue = api_get(repository, "/issues/" + str(envelope["task_issue"]), token)
    if not isinstance(issue, dict) or issue.get("state") != "open" or issue.get("number") != envelope["task_issue"]:
        raise GuardError("Linked task Issue must be open and match the PR envelope.")
    labels = issue.get("labels")
    if not isinstance(labels, list) or not any(isinstance(x, dict) and x.get("name") == TASK_LABEL for x in labels):
        raise GuardError("Linked Issue is missing agent-task label.")
    try:
        task = validate_issue_body(
            issue.get("body"), repository_metadata=live_repository,
            allow_legacy_jet_vpn=True,
        )
    except GitHubTaskError as exc:
        raise GuardError("Linked Issue task payload is invalid.") from exc
    project_binding = None
    if task["schema_version"] == 2:
        try:
            schema, manifests = load_project_configuration(Path(__file__).resolve().parents[2])
            project_binding = validate_task_project_binding(
                task, live_repository, schema=schema, project_manifests=manifests
            )
        except IntakeError as exc:
            raise GuardError("Linked Issue project binding is invalid or inactive.") from exc
    if task["schema_version"] == 1 and envelope["schema_version"] != 1:
        raise GuardError("Legacy v1 tasks require a v1 PR authorization envelope.")
    if task["schema_version"] == 2:
        if envelope["schema_version"] != 2:
            raise GuardError("Project-bound v2 tasks require a v2 PR authorization envelope.")
        issue_body = issue.get("body")
        issue_digest = hashlib.sha256(issue_body.encode("utf-8")).hexdigest() if isinstance(issue_body, str) else None
        if envelope["issue_body_sha256"] != issue_digest or envelope["project_binding"] != project_binding:
            raise GuardError("PR authorization envelope differs from the exact current Issue body or project binding.")
    if task["assigned_agent"] not in {"any", envelope["owner"]}:
        raise GuardError("PR owner does not match task assignment.")

    lease = read_lease(repository, task["task_id"], token, project_binding)
    if task["schema_version"] == 2 and envelope["base_sha"] != lease["base_sha"]:
        raise GuardError("PR authorization envelope differs from the lease-pinned base SHA.")
    if (lease["task_id"] != task["task_id"] or lease["owner"] != envelope["owner"]
            or lease["claim_id"] != envelope["claim_id"] or lease["status"] != "active"
            or lease.get("project_binding") != project_binding):
        raise GuardError("PR does not match the active task lease.")
    moment = datetime.fromisoformat((now or datetime.now(timezone.utc).isoformat()).replace("Z", "+00:00"))
    expires = datetime.fromisoformat(lease["expires_at"].replace("Z", "+00:00"))
    if expires <= moment:
        raise GuardError("Task lease has expired; renew before submitting.")
    compare = api_get(repository, "/compare/" + lease["base_sha"] + "..." + head_sha, token)
    merge_base = compare.get("merge_base_commit", {}).get("sha") if isinstance(compare, dict) else None
    if merge_base != lease["base_sha"]:
        raise GuardError("PR branch is not based on the pinned task SHA.")
    files = changed_files(repository, number, token)
    paths = validate_paths(files, task["allow"], task["exclude"])
    result = {"status": "validated-agent-pr", "pr_number": number,
              "task_issue": envelope["task_issue"], "task_id": task["task_id"],
              "owner": lease["owner"], "claim_id": lease["claim_id"],
              "base_sha": lease["base_sha"], "changed_paths": paths,
              "file_count": len(paths), "lease_status": lease["status"]}
    if project_binding is not None:
        result["project_binding"] = project_binding
    return result


def write_summary(result):
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if not target:
        return
    if result["status"] == "not-agent-pr":
        lines = ["## Agent PR guard", "", "Validated ordinary PR changed paths; no protected automation paths found.", "",
                 "- PR: #" + str(result["pr_number"]),
                 "- Changed files: " + str(result["file_count"]), "", "### Accepted paths"]
        lines.extend("- " + path for path in result["changed_paths"])
        text = "\n".join(lines) + "\n"
    else:
        lines = ["## Agent PR guard", "", "Validated task lease and PR scope.", "",
                 "- PR: #" + str(result["pr_number"]),
                 "- Task Issue: #" + str(result["task_issue"]) + " (" + result["task_id"] + ")",
                 "- Owner: " + result["owner"], "- Lease: " + result["lease_status"],
                 "- Pinned base SHA: " + result["base_sha"],
                 "- Changed files: " + str(result["file_count"]), "", "### Accepted paths"]
        lines.extend("- " + path for path in result["changed_paths"])
        text = "\n".join(lines) + "\n"
    Path(target).write_text(text, encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-file", required=True)
    args = parser.parse_args(argv)
    try:
        event = json.loads(Path(args.event_file).read_text(encoding="utf-8"))
        result = validate_agent_pr(event, token=os.environ.get("GITHUB_TOKEN", ""),
                                   repository=os.environ.get("GITHUB_REPOSITORY", ""))
        write_summary(result)
    except (OSError, UnicodeError, json.JSONDecodeError, GuardError) as exc:
        parser.error(str(exc))
    print(("Validated ordinary PR #" + str(result["pr_number"]) +
           " (no protected automation paths).") if result["status"] == "not-agent-pr" else
          "Validated agent PR #" + str(result["pr_number"]) + ".")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
