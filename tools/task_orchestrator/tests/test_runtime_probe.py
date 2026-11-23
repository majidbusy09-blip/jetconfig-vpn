import tempfile
import unittest
from pathlib import Path

from tools.task_orchestrator.runtime_probe import (
    RUNTIME_TOOLS, build_cgroup_report, build_report,
)


class RuntimeProbeTests(unittest.TestCase):
    def test_report_is_explicitly_inventory_only(self):
        report = build_report(
            tool_paths={name: None for name in RUNTIME_TOOLS},
            effective_uid=1001,
            kernel_release="test-kernel",
            proc_status="Name:\tpython\nSeccomp:\t2",
            namespace_names=["mnt", "net", "user"],
            cgroup_controllers="cpu memory pids",
            userns_max="65536",
            unprivileged_userns_clone="1",
            docker_socket_present=False,
            cgroup_report={"delegation_candidate": False},
        )
        self.assertEqual(report["classification"], "inventory_only_not_sandbox")
        self.assertFalse(report["eligible_for_untrusted_agent_execution"])
        self.assertTrue(report["host"]["running_as_non_root"])
        self.assertEqual(report["seccomp_mode"], 2)
        self.assertEqual(report["cgroup_controllers"], ["cpu", "memory", "pids"])
        self.assertEqual(report["namespaces_visible"], ["mnt", "net", "user"])
        self.assertFalse(report["cgroup_current_process"]["delegation_candidate"])

    def test_missing_host_features_are_reported_as_unknown_or_unavailable(self):
        report = build_report(
            tool_paths={"docker": "/usr/bin/docker"},
            effective_uid=0,
            kernel_release="",
            proc_status=None,
            namespace_names=[],
            cgroup_controllers=None,
            userns_max=None,
            unprivileged_userns_clone=None,
            docker_socket_present=True,
        )
        self.assertFalse(report["host"]["running_as_non_root"])
        self.assertIsNone(report["seccomp_mode"])
        self.assertFalse(report["cgroup_v2_available"])
        self.assertTrue(report["docker_socket_present"])
        self.assertFalse(report["eligible_for_untrusted_agent_execution"])
        self.assertIn("docker", report["runtime_tool_paths"])
        self.assertIsNone(report["runtime_tool_paths"]["podman"])

    def test_cgroup_report_reads_delegation_indicators_without_writing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            group = root / "job" / "worker"
            group.mkdir(parents=True)
            (group / "cgroup.controllers").write_text("cpu memory pids")
            (group / "cgroup.subtree_control").write_text("")
            (group / "cpu.max").write_text("max 100000")
            (group / "memory.max").write_text("max")
            (group / "pids.max").write_text("max")

            report = build_cgroup_report(
                cgroup_root=str(root),
                process_cgroup="0::/job/worker",
            )

            self.assertTrue(report["directory_visible"])
            self.assertEqual(report["controllers"], ["cpu", "memory", "pids"])
            self.assertEqual(report["limits"]["cpu.max"], "max 100000")
            self.assertTrue(report["delegation_candidate"])

    def test_cgroup_report_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as temporary:
            report = build_cgroup_report(
                cgroup_root=temporary,
                process_cgroup="0::/../../outside",
            )
            self.assertFalse(report["directory_visible"])
            self.assertFalse(report["delegation_candidate"])


if __name__ == "__main__":
    unittest.main()
