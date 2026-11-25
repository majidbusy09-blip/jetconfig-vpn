from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]


class CentralTaskInboxWorkflowTests(unittest.TestCase):
    def test_dispatches_are_serialized_per_repository_and_issue_not_globally(self):
        workflow = (ROOT / ".github/workflows/central-task-inbox.yml").read_text(encoding="utf-8")
        self.assertIn(
            "group: jet-ai-central-task-inbox-${{ github.event.client_payload.target_repository_id }}-${{ github.event.client_payload.issue_number }}",
            workflow,
        )
        self.assertIn("cancel-in-progress: false", workflow)

    def test_concurrent_durable_branch_pushes_rebase_and_retry(self):
        workflow = (ROOT / ".github/workflows/central-task-inbox.yml").read_text(encoding="utf-8")
        self.assertIn("for attempt in 1 2 3; do", workflow)
        self.assertIn("git rebase origin/task-inbox", workflow)
        self.assertIn("git push origin HEAD:refs/heads/task-inbox", workflow)
        self.assertIn("Unable to persist inbox record after three safe push attempts.", workflow)


if __name__ == "__main__":
    unittest.main()
