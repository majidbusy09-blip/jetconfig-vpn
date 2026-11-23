import unittest

from tools.task_orchestrator.runtime_acceptance_probe import build_command


class RuntimeAcceptanceProbeTests(unittest.TestCase):
    def test_command_uses_fixed_isolation_flags_and_no_host_root_mount(self):
        command = build_command(
            "/usr/bin/bwrap", "/tmp/source", "/tmp/scratch",
            "/tmp/host-sentinel", 12345,
        )
        self.assertIn("--unshare-user", command)
        self.assertIn("--unshare-pid", command)
        self.assertIn("--unshare-net", command)
        self.assertIn("--clearenv", command)
        self.assertIn("--ro-bind", command)
        self.assertIn("/workspace", command)
        self.assertIn("--bind", command)
        self.assertNotIn("/", command[command.index("--ro-bind") + 1:command.index("--ro-bind") + 2])
        self.assertNotIn("/var/run/docker.sock", command)
        self.assertIn("/usr/bin/python3", command)

    def test_command_does_not_mount_runner_home_or_docker_socket(self):
        command = build_command(
            "/usr/bin/bwrap", "/tmp/source", "/tmp/scratch",
            "/tmp/host-sentinel", 12345,
        )
        joined = " ".join(command)
        self.assertNotIn("/home/runner", joined)
        self.assertNotIn("/var/run/docker.sock", joined)
        self.assertNotIn("--ro-bind / /", joined)


if __name__ == "__main__":
    unittest.main()
