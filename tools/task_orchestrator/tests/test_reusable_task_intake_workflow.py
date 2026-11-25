import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


class ReusableTaskIntakeWorkflowTests(unittest.TestCase):
    def test_reusable_workflow_checks_out_caller_and_trusted_control_plane_separately(self):
        workflow = (ROOT / ".github/workflows/agent-task-intake-reusable.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_call:", workflow)
        self.assertIn("actions/checkout@v4", workflow)
        self.assertIn("repository: majidbusy09-blip/jetconfig-vpn", workflow)
        self.assertIn("ref: 053c1f6e3a695cc8675bc90a679c554ed0e83f18", workflow)
        self.assertNotIn("github.workflow_sha", workflow)
        self.assertNotIn("ref: main", workflow)
        self.assertIn("path: .jet-ai/central", workflow)
        self.assertIn("PYTHONPATH: ${{ github.workspace }}/.jet-ai/central", workflow)
        self.assertIn('python -m tools.task_orchestrator.github_issue_intake', workflow)
        self.assertIn('"$GITHUB_EVENT_PATH"', workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("issues: read", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("issues: write", workflow)

    def test_first_party_intake_workflow_uses_single_admission_event_without_opened_duplicates(self):
        workflow = (ROOT / ".github/workflows/agent-task-intake.yml").read_text(encoding="utf-8")
        self.assertIn("issues:", workflow)
        self.assertIn("types: [labeled, edited]", workflow)
        self.assertNotIn("types: [opened, labeled, edited]", workflow)
        self.assertIn("uses: ./.github/workflows/agent-task-intake-reusable.yml", workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("issues: read", workflow)


if __name__ == "__main__":
    unittest.main()
