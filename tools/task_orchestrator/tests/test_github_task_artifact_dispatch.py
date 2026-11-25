import copy
import hashlib
import json
import unittest

from tools.task_orchestrator.github_task_artifact_dispatch import (
    DispatchError, validate_dispatch_event, validate_remote_metadata, validate_issue_snapshot,
)

MANIFEST = {
    "project_id": "hesabgar-man",
    "repository": {"repository_id": "1423683236", "full_name": "majidbusy09-blip/hesabgar_man"},
}
PAYLOAD = {
    "target_repository": "majidbusy09-blip/hesabgar_man",
    "target_repository_id": 1423683236,
    "issue_number": 17,
    "workflow_run_id": 123456,
    "artifact_id": 987654,
    "artifact_name": "agent-task-17",
    "source_sha": "a" * 40,
}
EVENT = {"action": "jet-ai-task-artifact-ready", "client_payload": PAYLOAD}
REPOSITORY = {
    "id": 1423683236, "full_name": "majidbusy09-blip/hesabgar_man",
    "html_url": "https://github.com/majidbusy09-blip/hesabgar_man",
    "default_branch": "main",
}
ARTIFACT = {
    "id": 987654, "name": "agent-task-17", "expired": False,
    "size_in_bytes": 1005,
    "workflow_run": {
        "id": 123456, "repository_id": 1423683236,
        "head_repository_id": 1423683236, "head_sha": "a" * 40,
    },
}


class GitHubTaskArtifactDispatchTests(unittest.TestCase):
    def test_accepts_exact_registered_repository_artifact_and_run(self):
        dispatch = validate_dispatch_event(EVENT, [MANIFEST])
        result = validate_remote_metadata(
            dispatch, artifact_metadata=ARTIFACT, repository_metadata=REPOSITORY,
        )
        self.assertEqual(result["project_id"], "hesabgar-man")
        self.assertEqual(result["artifact_size_in_bytes"], 1005)

    def test_rejects_unknown_repository_and_mutated_dispatch_fields(self):
        with self.assertRaises(DispatchError):
            validate_dispatch_event(EVENT, [])
        bad = copy.deepcopy(EVENT)
        bad["client_payload"]["artifact_name"] = "other"
        with self.assertRaises(DispatchError):
            validate_dispatch_event(bad, [MANIFEST])
        bad = copy.deepcopy(EVENT)
        bad["client_payload"]["target_repository_id"] = "../escape"
        with self.assertRaises(DispatchError):
            validate_dispatch_event(bad, [MANIFEST])

    def test_rejects_artifact_from_another_run_repository_or_revision(self):
        dispatch = validate_dispatch_event(EVENT, [MANIFEST])
        for key, value in (
            ("id", 999), ("name", "other"), ("expired", True),
        ):
            bad = copy.deepcopy(ARTIFACT)
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(DispatchError):
                validate_remote_metadata(dispatch, artifact_metadata=bad, repository_metadata=REPOSITORY)
        for key, value in (
            ("id", 999), ("head_repository_id", 999), ("head_sha", "b" * 40),
        ):
            bad = copy.deepcopy(ARTIFACT)
            bad["workflow_run"][key] = value
            with self.subTest(workflow_field=key), self.assertRaises(DispatchError):
                validate_remote_metadata(dispatch, artifact_metadata=bad, repository_metadata=REPOSITORY)

    def test_rejects_repository_metadata_identity_mismatch(self):
        dispatch = validate_dispatch_event(EVENT, [MANIFEST])
        bad = dict(REPOSITORY, id=999)
        with self.assertRaises(DispatchError):
            validate_remote_metadata(dispatch, artifact_metadata=ARTIFACT, repository_metadata=bad)

    def test_live_issue_snapshot_must_match_exact_body_label_and_open_state(self):
        dispatch = validate_dispatch_event(EVENT, [MANIFEST])
        task = {
            "schema_version": 2, "task_id": "sample-task",
            "goal": "A bounded task for issue snapshot validation.",
            "capability": "investigation", "risk": "low", "assigned_agent": "any",
            "allow": ["docs/**"], "exclude": [],
            "scope_reason": "Read-only snapshot test.",
            "verification_profiles": ["python-tooling-tests"],
            "project_binding": {
                "project_id": "hesabgar-man", "repository_id": "1423683236",
                "repository_full_name": "majidbusy09-blip/hesabgar_man",
                "default_branch": "main", "manifest_schema_version": 1,
                "manifest_sha256": "b" * 64,
            },
        }
        body = "<!-- jet-agent-task:v2 -->\n" + "```json\n" + json.dumps(task) + "\n" + "```"
        artifact = {
            "issue_number": 17, "issue_title": "Task title",
            "issue_body_sha256": hashlib.sha256(body.encode()).hexdigest(),
            "task": task,
        }
        issue = {
            "number": 17, "title": "Task title",
            "html_url": "https://github.com/majidbusy09-blip/hesabgar_man/issues/17",
            "state": "open", "body": body,
            "labels": [{"name": "agent-task"}],
        }
        validate_issue_snapshot(dispatch, intake_artifact=artifact,
                                issue_metadata=issue, repository_metadata=REPOSITORY)
        changed = dict(issue, state="closed")
        with self.assertRaises(DispatchError):
            validate_issue_snapshot(dispatch, intake_artifact=artifact,
                                    issue_metadata=changed, repository_metadata=REPOSITORY)
        changed = dict(issue, body=body + "\nEdited after intake")
        with self.assertRaises(DispatchError):
            validate_issue_snapshot(dispatch, intake_artifact=artifact,
                                    issue_metadata=changed, repository_metadata=REPOSITORY)
        changed = dict(issue, labels=[])
        with self.assertRaises(DispatchError):
            validate_issue_snapshot(dispatch, intake_artifact=artifact,
                                    issue_metadata=changed, repository_metadata=REPOSITORY)


if __name__ == "__main__":
    unittest.main()
