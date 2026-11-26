import base64
import copy
import io
import json
import os
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from tools.task_orchestrator.github_lease import make_lease, lock_branch
from tools.task_orchestrator.github_task_handoff import build_task_handoff
from tools.task_orchestrator.project_registry import manifest_digest
from tools.task_orchestrator import task_orchestrator as orchestrator
from tools.task_orchestrator.github_task_handoff_accept import (
    HandoffAcceptanceError, validate_handoff_for_acceptance, _read_json,
    accept_handoff, validate_agent_input_path, write_agent_input_github_output,
    _read_current_lease,
)

REPOSITORY = "majidbusy09-blip/jetconfig-vpn"
REPOSITORY_METADATA = {"id": 1349356614, "full_name": REPOSITORY, "html_url": "https://github.com/" + REPOSITORY, "default_branch": "main"}
TASK_ID = "sample-task"
CLAIM = "a" * 16
BASE = "b" * 40
LOCK_COMMIT = "c" * 40
NOW = "2029-12-31T23:00:00Z"
EXPIRES = "2030-01-01T01:00:00Z"
ROOT = Path(__file__).resolve().parents[3]
PROJECT_SCHEMA = json.loads((ROOT / "docs/PROJECT_MANIFEST_SCHEMA.json").read_text(encoding="utf-8"))
ACTIVE_MANIFEST = copy.deepcopy(PROJECT_SCHEMA["examples"][0])
ACTIVE_MANIFEST["lifecycle"] = "active"


def issue_event(operation="claim", claim_id=CLAIM, previous_claim_id=CLAIM):
    import json
    task = {
        "schema_version": 1, "task_id": TASK_ID,
        "goal": "A bounded task for the handoff acceptance test.",
        "capability": "documentation", "risk": "low",
        "assigned_agent": "any", "allow": ["docs/**"], "exclude": [],
        "scope_reason": "Documentation-only.", "verification_profiles": ["python-tooling-tests"],
    }
    body = "<!-- jet-agent-task:v1 -->\n\n" + "```json\n" + json.dumps(task) + "\n```"
    return {
        "action": "created",
        "repository": dict(REPOSITORY_METADATA),
        "issue": {
            "number": 42, "state": "open", "body": body,
            "html_url": "https://github.com/majidbusy09-blip/jetconfig-vpn/issues/42",
            "labels": [{"name": "agent-task"}],
        },
        "comment": {"body": (f"/jet-agent claim chatgpt {claim_id}" if operation == "claim" else f"/jet-agent renew chatgpt {previous_claim_id} {claim_id}"), "author_association": "OWNER"},
    }


def manifest():
    event = issue_event()
    import json
    task = json.loads(event["issue"]["body"].split("```json\n", 1)[1].split("\n```", 1)[0])
    result = {
        "operation": "claim", "task_id": TASK_ID, "issue_number": 42,
        "issue_url": event["issue"]["html_url"],
        "result": {
            "task_id": TASK_ID, "owner": "chatgpt", "claim_id": CLAIM,
            "status": "active", "base_sha": BASE, "expires_at": EXPIRES,
            "lock_branch": "agent-locks/" + TASK_ID,
            "lock_commit": LOCK_COMMIT, "verified": True,
        },
    }
    return build_task_handoff(event, result, run_id=123, run_attempt=1, now=NOW)


def current_issue():
    event = issue_event()
    return {
        "number": 42, "state": "open", "body": event["issue"]["body"],
        "html_url": event["issue"]["html_url"],
        "labels": [{"name": "agent-task"}],
    }


def current_lease():
    return make_lease(
        task_id=TASK_ID, owner="chatgpt", claim_id=CLAIM,
        base_sha=BASE, now="2029-12-31T23:00:00Z", duration_minutes=120,
    )


def v2_issue_event(operation="claim", claim_id=CLAIM, previous_claim_id=CLAIM):
    task = {
        "schema_version": 2, "task_id": TASK_ID,
        "goal": "A bounded task for the handoff acceptance test.",
        "capability": "documentation", "risk": "low",
        "assigned_agent": "any", "allow": ["docs/**"], "exclude": [],
        "scope_reason": "Documentation-only.", "verification_profiles": ["python-tooling-tests"],
        "project_binding": {
            "project_id": ACTIVE_MANIFEST["project_id"],
            "repository_id": ACTIVE_MANIFEST["repository"]["repository_id"],
            "repository_full_name": ACTIVE_MANIFEST["repository"]["full_name"],
            "default_branch": ACTIVE_MANIFEST["repository"]["default_branch"],
            "manifest_schema_version": ACTIVE_MANIFEST["schema_version"],
            "manifest_sha256": manifest_digest(ACTIVE_MANIFEST),
        },
    }
    body = "<!-- jet-agent-task:v2 -->\n\n" + "```json\n" + json.dumps(task) + "\n```"
    ev = issue_event(operation, claim_id, previous_claim_id)
    ev["issue"]["body"] = body
    return ev


def v2_current_issue():
    ev = v2_issue_event()
    return {
        "number": 42, "state": "open", "body": ev["issue"]["body"],
        "html_url": ev["issue"]["html_url"],
        "labels": [{"name": "agent-task"}],
    }


def v2_handoff(operation="claim", claim_id=CLAIM, previous_claim_id=CLAIM, base_sha=BASE, lock_commit=LOCK_COMMIT, run_id=321):
    ev = v2_issue_event(operation, claim_id, previous_claim_id)
    binding = {
        "project_id": ACTIVE_MANIFEST["project_id"],
        "repository_id": ACTIVE_MANIFEST["repository"]["repository_id"],
        "repository_full_name": ACTIVE_MANIFEST["repository"]["full_name"],
        "default_branch": ACTIVE_MANIFEST["repository"]["default_branch"],
        "manifest_schema_version": ACTIVE_MANIFEST["schema_version"],
        "manifest_sha256": manifest_digest(ACTIVE_MANIFEST),
    }
    lease_record = make_lease(
        task_id=TASK_ID, owner="chatgpt", claim_id=claim_id,
        base_sha=base_sha, now=NOW, duration_minutes=120, project_binding=binding,
    )
    lease_result = {
        "operation": operation, "task_id": TASK_ID, "issue_number": 42,
        "issue_url": ev["issue"]["html_url"],
        "result": {
            "task_id": TASK_ID, "owner": "chatgpt", "claim_id": claim_id,
            "status": "active", "base_sha": base_sha,
            "expires_at": lease_record["expires_at"],
            "lock_branch": lock_branch(TASK_ID, binding),
            "lock_commit": lock_commit, "verified": True,
            "project_binding": binding,
        },
    }
    with patch(
        "tools.task_orchestrator.github_issue_lease_command.load_project_configuration",
        return_value=(PROJECT_SCHEMA, [ACTIVE_MANIFEST]),
    ), patch(
        "tools.task_orchestrator.github_task_handoff.load_project_configuration",
        return_value=(PROJECT_SCHEMA, [ACTIVE_MANIFEST]),
    ):
        return build_task_handoff(ev, lease_result, run_id=run_id, run_attempt=1, now=NOW), lease_record


class HandoffAcceptanceTests(unittest.TestCase):
    def test_accepts_current_issue_and_exact_active_remote_lease(self):
        accepted = validate_handoff_for_acceptance(
            manifest(), current_issue(), current_lease(), LOCK_COMMIT,
            repository=REPOSITORY, repository_metadata=REPOSITORY_METADATA, now=NOW,
        )
        self.assertEqual(accepted["task_id"], TASK_ID)
        self.assertEqual(accepted["assigned_agent"], "any")

    def test_rejects_changed_or_closed_issue(self):
        for mutate in (
            lambda issue: issue.update(state="closed"),
            lambda issue: issue.update(body=issue["body"] + "\nchanged"),
            lambda issue: issue.update(labels=[]),
            lambda issue: issue.update(number=99),
            lambda issue: issue.update(html_url="https://github.com/majidbusy09-blip/jetconfig-vpn/issues/99"),
        ):
            issue = current_issue()
            mutate(issue)
            with self.subTest(issue=issue), self.assertRaises(HandoffAcceptanceError):
                validate_handoff_for_acceptance(
                    manifest(), issue, current_lease(), LOCK_COMMIT,
                    repository=REPOSITORY, repository_metadata=REPOSITORY_METADATA, now=NOW,
                )

    def test_rejects_mismatched_task_lease_and_lock_ref(self):
        for lease_mutation, lock_sha in (
            ({"claim_id": "d" * 16}, LOCK_COMMIT),
            ({"owner": "grok"}, LOCK_COMMIT),
            ({"base_sha": "e" * 40}, LOCK_COMMIT),
            ({"status": "released"}, LOCK_COMMIT),
            ({}, "f" * 40),
        ):
            lease = current_lease()
            lease.update(lease_mutation)
            with self.subTest(lease=lease, lock_sha=lock_sha), self.assertRaises(HandoffAcceptanceError):
                validate_handoff_for_acceptance(
                    manifest(), current_issue(), lease, lock_sha,
                    repository=REPOSITORY, repository_metadata=REPOSITORY_METADATA, now=NOW,
                )

    def test_rejects_modified_manifest_and_wrong_repository(self):
        payload = manifest()
        payload["task"]["goal"] = "Tampered goal"
        with self.assertRaises(HandoffAcceptanceError):
            validate_handoff_for_acceptance(
                payload, current_issue(), current_lease(), LOCK_COMMIT,
                repository=REPOSITORY, repository_metadata=REPOSITORY_METADATA, now=NOW,
            )
        with self.assertRaises(HandoffAcceptanceError):
            validate_handoff_for_acceptance(
                manifest(), current_issue(), current_lease(), LOCK_COMMIT,
                repository="other/repository", repository_metadata=REPOSITORY_METADATA, now=NOW,
            )

    def test_rejects_expired_lease_and_execution_flags(self):
        lease = current_lease()
        lease["expires_at"] = "2029-12-31T22:59:59Z"
        with self.assertRaises(HandoffAcceptanceError):
            validate_handoff_for_acceptance(
                manifest(), current_issue(), lease, LOCK_COMMIT,
                repository=REPOSITORY, repository_metadata=REPOSITORY_METADATA, now=NOW,
            )
        for invalid_flag in (True, 0, "false"):
            payload = manifest()
            payload["execution"]["model_called"] = invalid_flag
            with self.subTest(invalid_flag=invalid_flag), self.assertRaises(HandoffAcceptanceError):
                validate_handoff_for_acceptance(
                    payload, current_issue(), current_lease(), LOCK_COMMIT,
                    repository=REPOSITORY, repository_metadata=REPOSITORY_METADATA, now=NOW,
                )


    def test_accepts_v2_project_binding_and_persists_it_with_pinned_base_sha(self):
        handoff, lease_record = v2_handoff()
        accepted = validate_handoff_for_acceptance(
            handoff, v2_current_issue(), lease_record, LOCK_COMMIT,
            repository=REPOSITORY, repository_metadata=REPOSITORY_METADATA,
            project_schema=PROJECT_SCHEMA, project_manifests=[ACTIVE_MANIFEST], now=NOW,
        )
        self.assertEqual(accepted["schema_version"], 2)
        self.assertEqual(handoff["handoff_schema"], 3)

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "repository"
            root.mkdir()
            def git(*args):
                return subprocess.run(
                    ["git", *args], cwd=root, check=True, capture_output=True, text=True
                ).stdout.strip()
            git("init", "-q")
            git("config", "user.name", "Handoff Acceptance Test")
            git("config", "user.email", "handoff-test@example.invalid")
            git("remote", "add", "origin", "https://github.com/majidbusy09-blip/jetconfig-vpn.git")
            docs = {
                "AGENTS.md": "Project agent instructions.\n",
                "docs/PROJECT_CONTEXT.md": "Project context.\n",
                "docs/CURRENT_STATUS.md": "Current status.\n",
                "docs/NEXT_STEPS.md": "Next steps.\n",
                "docs/TASK_TEMPLATE.md": "Task template.\n",
                "docs/DEVELOPMENT_LOG.md": "Development log.\n",
            }
            for name, content in docs.items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            git("add", ".")
            git("commit", "-m", "fixture base")
            base_sha = git("rev-parse", "HEAD")
            handoff, lease_record = v2_handoff(base_sha=base_sha, run_id=322)
            artifact = Path(folder) / "task-handoff.json"
            artifact.write_text(json.dumps(handoff), encoding="utf-8")
            previous = Path.cwd()
            try:
                os.chdir(root)
                with patch(
                    "tools.task_orchestrator.github_task_handoff_accept.api_get",
                    side_effect=[v2_current_issue(), REPOSITORY_METADATA],
                ), patch(
                    "tools.task_orchestrator.github_task_handoff_accept.load_project_configuration",
                    return_value=(PROJECT_SCHEMA, [ACTIVE_MANIFEST]),
                ), patch(
                    "tools.task_orchestrator.github_task_handoff_accept._read_current_lease",
                    return_value=(lease_record, LOCK_COMMIT),
                ):
                    output = accept_handoff(
                        artifact, token="read-token", repository=REPOSITORY, create_branch=True,
                    )
            finally:
                os.chdir(previous)
            expected = dict(handoff["project_binding"], base_sha=base_sha)
            task_directory = (
                root / ".agent" / "tasks" / expected["project_id"]
                / expected["repository_id"] / TASK_ID
            )
            record = json.loads((task_directory / "task.json").read_text(encoding="utf-8"))
            self.assertEqual(
                git("branch", "--show-current"),
                "agent/projects/" + expected["project_id"] + "/" + expected["repository_id"] + "/" + TASK_ID,
            )
            self.assertEqual(record["github_project_binding"], expected)
            required = ACTIVE_MANIFEST["memory"]["required_documents"]
            self.assertEqual(record["required_context"], required)
            self.assertEqual(record["project_memory_manifest"], {
                "version": ACTIVE_MANIFEST["memory"]["manifest_version"],
                "required_documents": required,
                "max_total_bytes": ACTIVE_MANIFEST["memory"]["max_total_bytes"],
            })
            envelope = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(envelope["project_binding"], expected)
            self.assertEqual(envelope["memory_manifest"]["required_documents"], required)
            self.assertEqual([item["path"] for item in envelope["project_context"]], required)
            self.assertNotIn("docs/TASK_TEMPLATE.md", required)
            self.assertEqual(record["github_handoff"]["base_sha"], base_sha)


    def test_reads_single_file_github_artifact_zip_without_extracting_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            good = Path(folder) / "handoff.zip"
            payload = io.BytesIO()
            with zipfile.ZipFile(payload, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("task-handoff.json", json.dumps({"handoff_schema": 1}))
            good.write_bytes(payload.getvalue())
            self.assertEqual(_read_json(good), {"handoff_schema": 1})

            bad = Path(folder) / "unsafe.zip"
            payload = io.BytesIO()
            with zipfile.ZipFile(payload, "w") as archive:
                archive.writestr("../task-handoff.json", "{}")
            bad.write_bytes(payload.getvalue())
            with self.assertRaises(HandoffAcceptanceError):
                _read_json(bad)


    def test_remote_lease_read_is_bound_to_a_stable_ref_sha(self):
        record = current_lease()
        encoded = base64.b64encode(
            json.dumps(record).encode("utf-8")
        ).decode("ascii")
        ref = {"object": {"sha": LOCK_COMMIT, "type": "commit"}}
        content = {"encoding": "base64", "content": encoded}
        with patch(
            "tools.task_orchestrator.github_task_handoff_accept.api_get",
            side_effect=[ref, content, ref],
        ):
            loaded, commit = _read_current_lease(REPOSITORY, TASK_ID, "read-token")
        self.assertEqual(loaded, record)
        self.assertEqual(commit, LOCK_COMMIT)

        moved = {"object": {"sha": "d" * 40, "type": "commit"}}
        with patch(
            "tools.task_orchestrator.github_task_handoff_accept.api_get",
            side_effect=[ref, content, moved],
        ):
            with self.assertRaisesRegex(HandoffAcceptanceError, "moved"):
                _read_current_lease(REPOSITORY, TASK_ID, "read-token")


    def test_accept_handoff_builds_local_envelope_on_exact_pinned_branch(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "repository"
            root.mkdir()
            def git(*args):
                return subprocess.run(
                    ["git", *args], cwd=root, check=True, capture_output=True, text=True
                ).stdout.strip()

            git("init", "-q")
            git("config", "user.name", "Handoff Acceptance Test")
            git("config", "user.email", "handoff-test@example.invalid")
            git("remote", "add", "origin", "https://github.com/majidbusy09-blip/jetconfig-vpn.git")
            docs = {
                "AGENTS.md": "Project agent instructions.\n",
                "docs/PROJECT_CONTEXT.md": "Project context.\n",
                "docs/CURRENT_STATUS.md": "Current status.\n",
                "docs/NEXT_STEPS.md": "Next steps.\n",
                "docs/TASK_TEMPLATE.md": "Task template.\n",
                "docs/DEVELOPMENT_LOG.md": "Development log.\n",
            }
            for name, body in docs.items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(body, encoding="utf-8")
            git("add", ".")
            git("commit", "-m", "fixture base")
            base_sha = git("rev-parse", "HEAD")

            event_payload = issue_event()
            lease_record = make_lease(
                task_id=TASK_ID, owner="chatgpt", claim_id=CLAIM,
                base_sha=base_sha, now=NOW, duration_minutes=120,
            )
            lease_payload = {
                "operation": "claim", "task_id": TASK_ID, "issue_number": 42,
                "issue_url": "https://github.com/majidbusy09-blip/jetconfig-vpn/issues/42",
                "result": {
                    "task_id": TASK_ID, "owner": "chatgpt", "claim_id": CLAIM,
                    "status": "active", "base_sha": base_sha,
                    "expires_at": lease_record["expires_at"],
                    "lock_branch": "agent-locks/" + TASK_ID,
                    "lock_commit": LOCK_COMMIT, "verified": True,
                },
            }
            handoff = build_task_handoff(
                event_payload, lease_payload, run_id=123, run_attempt=1, now=NOW
            )
            artifact = Path(folder) / "task-handoff.json"
            artifact.write_text(json.dumps(handoff), encoding="utf-8")
            issue = current_issue()
            previous = Path.cwd()
            try:
                os.chdir(root)
                with patch(
                    "tools.task_orchestrator.github_task_handoff_accept.api_get",
                    side_effect=[issue, REPOSITORY_METADATA],
                ), patch(
                    "tools.task_orchestrator.github_task_handoff_accept._read_current_lease",
                    return_value=(lease_record, LOCK_COMMIT),
                ):
                    output = accept_handoff(
                        artifact, token="read-token", repository=REPOSITORY,
                        create_branch=True,
                    )
            finally:
                os.chdir(previous)

            self.assertTrue(output.is_file())
            envelope = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(envelope["task_id"], TASK_ID)
            self.assertEqual(git("branch", "--show-current"), "agent/" + TASK_ID)
            self.assertEqual(len(envelope["project_context"]), 6)
            self.assertEqual(envelope["source_context"], [])
            record = json.loads(
                (root / ".agent" / "tasks" / TASK_ID / "task.json").read_text(encoding="utf-8")
            )
            self.assertEqual(record["github_handoff"]["issue_number"], 42)
            self.assertEqual(record["github_handoff"]["claim_id"], CLAIM)
            self.assertEqual(git("rev-parse", "HEAD"), base_sha)

            # Simulate implementation progress before a lease renewal.
            (root / "docs" / "work-in-progress.md").write_text("Local implementation work.\n", encoding="utf-8")
            git("add", "docs/work-in-progress.md")
            git("commit", "-m", "work in progress")
            branch_head = git("rev-parse", "HEAD")
            original_envelope = output.read_bytes()

            renewed_claim = "d" * 16
            renewed_now = "2029-12-31T23:30:00Z"
            renewed_lock = "e" * 40
            renewed_lease = make_lease(
                task_id=TASK_ID, owner="chatgpt", claim_id=renewed_claim,
                base_sha=base_sha, now=renewed_now, duration_minutes=120,
            )
            wrong_renewal_event = issue_event("renew", renewed_claim, "f" * 16)
            wrong_renewal_result = {
                "operation": "renew", "task_id": TASK_ID, "issue_number": 42,
                "issue_url": "https://github.com/majidbusy09-blip/jetconfig-vpn/issues/42",
                "result": {
                    "task_id": TASK_ID, "owner": "chatgpt", "claim_id": renewed_claim,
                    "status": "active", "base_sha": base_sha,
                    "expires_at": renewed_lease["expires_at"],
                    "lock_branch": "agent-locks/" + TASK_ID,
                    "lock_commit": renewed_lock, "verified": True,
                },
            }
            wrong_handoff = build_task_handoff(
                wrong_renewal_event, wrong_renewal_result,
                run_id=124, run_attempt=1, now=renewed_now,
            )
            artifact.write_text(json.dumps(wrong_handoff), encoding="utf-8")
            previous = Path.cwd()
            try:
                os.chdir(root)
                with patch(
                    "tools.task_orchestrator.github_task_handoff_accept.api_get",
                    side_effect=[issue, REPOSITORY_METADATA],
                ), patch(
                    "tools.task_orchestrator.github_task_handoff_accept._read_current_lease",
                    return_value=(renewed_lease, renewed_lock),
                ):
                    with self.assertRaisesRegex(HandoffAcceptanceError, "exact claim"):
                        accept_handoff(
                            artifact, token="read-token", repository=REPOSITORY,
                            refresh_existing=True,
                        )
            finally:
                os.chdir(previous)

            renewed_event = issue_event("renew", renewed_claim, CLAIM)
            renewed_result = {
                "operation": "renew", "task_id": TASK_ID, "issue_number": 42,
                "issue_url": "https://github.com/majidbusy09-blip/jetconfig-vpn/issues/42",
                "result": {
                    "task_id": TASK_ID, "owner": "chatgpt", "claim_id": renewed_claim,
                    "status": "active", "base_sha": base_sha,
                    "expires_at": renewed_lease["expires_at"],
                    "lock_branch": "agent-locks/" + TASK_ID,
                    "lock_commit": renewed_lock, "verified": True,
                },
            }
            renewed_handoff = build_task_handoff(
                renewed_event, renewed_result, run_id=124, run_attempt=1, now=renewed_now
            )
            artifact.write_text(json.dumps(renewed_handoff), encoding="utf-8")
            previous = Path.cwd()
            try:
                os.chdir(root)
                with patch(
                    "tools.task_orchestrator.github_task_handoff_accept.api_get",
                    side_effect=[issue, REPOSITORY_METADATA],
                ), patch(
                    "tools.task_orchestrator.github_task_handoff_accept._read_current_lease",
                    return_value=(renewed_lease, renewed_lock),
                ):
                    refreshed = accept_handoff(
                        artifact, token="read-token", repository=REPOSITORY,
                        refresh_existing=True,
                    )
            finally:
                os.chdir(previous)

            self.assertEqual(refreshed, output)
            self.assertEqual(output.read_bytes(), original_envelope)
            renewed_record = json.loads(
                (root / ".agent" / "tasks" / TASK_ID / "task.json").read_text(encoding="utf-8")
            )
            self.assertEqual(renewed_record["github_handoff"]["claim_id"], renewed_claim)
            self.assertEqual(renewed_record["github_handoff"]["lock_commit"], renewed_lock)
            self.assertEqual(git("rev-parse", "HEAD"), branch_head)

    def test_reads_project_scoped_lease_ref_and_record_path(self):
        from tools.task_orchestrator.project_namespace import lease_record_path
        binding = {
            "project_id": ACTIVE_MANIFEST["project_id"],
            "repository_id": ACTIVE_MANIFEST["repository"]["repository_id"],
            "repository_full_name": ACTIVE_MANIFEST["repository"]["full_name"],
            "default_branch": ACTIVE_MANIFEST["repository"]["default_branch"],
            "manifest_schema_version": ACTIVE_MANIFEST["schema_version"],
            "manifest_sha256": manifest_digest(ACTIVE_MANIFEST),
        }
        record = make_lease(
            task_id=TASK_ID, owner="chatgpt", claim_id=CLAIM, base_sha=BASE,
            now=NOW, duration_minutes=120, project_binding=binding,
        )
        encoded = base64.b64encode(json.dumps(record).encode("utf-8")).decode("ascii")
        ref = {"object": {"sha": LOCK_COMMIT, "type": "commit"}}
        contents = {"encoding": "base64", "content": encoded}
        with patch(
            "tools.task_orchestrator.github_task_handoff_accept.api_get",
            side_effect=[ref, contents, ref],
        ) as api:
            loaded, commit = _read_current_lease(REPOSITORY, TASK_ID, "read-token", binding)
        self.assertEqual(loaded, record)
        self.assertEqual(commit, LOCK_COMMIT)
        self.assertIn("agent-locks/projects/" + ACTIVE_MANIFEST["project_id"],
                      api.call_args_list[0].args[1])
        self.assertIn(lease_record_path(TASK_ID, binding), api.call_args_list[1].args[1])

    def test_agent_input_path_is_exact_and_project_scoped(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            legacy_record = orchestrator.task_path(root, TASK_ID)
            legacy_record.parent.mkdir(parents=True)
            legacy_output = legacy_record.parent / "agent_input.json"
            legacy_output.write_text("{}", encoding="utf-8")
            self.assertEqual(
                validate_agent_input_path(root, legacy_output, TASK_ID, None),
                ".agent/tasks/" + TASK_ID + "/agent_input.json",
            )

            binding = {
                "project_id": ACTIVE_MANIFEST["project_id"],
                "repository_id": ACTIVE_MANIFEST["repository"]["repository_id"],
                "repository_full_name": ACTIVE_MANIFEST["repository"]["full_name"],
                "default_branch": ACTIVE_MANIFEST["repository"]["default_branch"],
                "manifest_schema_version": ACTIVE_MANIFEST["schema_version"],
                "manifest_sha256": manifest_digest(ACTIVE_MANIFEST),
                "base_sha": BASE,
            }
            scoped_record = orchestrator.task_path(root, TASK_ID, binding)
            scoped_record.parent.mkdir(parents=True)
            scoped_output = scoped_record.parent / "agent_input.json"
            scoped_output.write_text("{}", encoding="utf-8")
            relative = validate_agent_input_path(root, scoped_output, TASK_ID, binding)
            self.assertEqual(relative.split("/")[-3:], [binding["repository_id"], TASK_ID, "agent_input.json"])

            other_binding = dict(binding, project_id="another-project")
            other_record = orchestrator.task_path(root, TASK_ID, other_binding)
            other_record.parent.mkdir(parents=True)
            other_output = other_record.parent / "agent_input.json"
            other_output.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(HandoffAcceptanceError, "exact accepted task namespace"):
                validate_agent_input_path(root, other_output, TASK_ID, binding)

            with self.assertRaisesRegex(HandoffAcceptanceError, "exact accepted task namespace"):
                validate_agent_input_path(root, legacy_output, "different-task", None)

    def test_agent_input_path_rejects_symlink_and_non_regular_target(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            record = orchestrator.task_path(root, TASK_ID)
            record.parent.mkdir(parents=True)
            target = record.parent / "agent_input.json"
            outside = root / "outside.json"
            outside.write_text("{}", encoding="utf-8")
            target.symlink_to(outside)
            with self.assertRaisesRegex(HandoffAcceptanceError, "symlink"):
                validate_agent_input_path(root, target, TASK_ID, None)

            target.unlink()
            target.mkdir()
            with self.assertRaisesRegex(HandoffAcceptanceError, "regular file"):
                validate_agent_input_path(root, target, TASK_ID, None)

    def test_github_output_contains_only_validated_agent_input_path(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "github-output"
            output.write_text("", encoding="utf-8")
            relative = ".agent/tasks/" + TASK_ID + "/agent_input.json"
            write_agent_input_github_output(output, relative)
            self.assertEqual(output.read_text(encoding="utf-8"), "agent_input_path=" + relative + "\\n")
            for invalid in ("../agent_input.json", "/tmp/agent_input.json", ".agent/tasks/x/input.json",
                            ".agent/tasks/x/agent_input.json\\nEVIL=value"):
                with self.subTest(path=invalid), self.assertRaises(HandoffAcceptanceError):
                    write_agent_input_github_output(output, invalid)


if __name__ == "__main__":
    unittest.main()
