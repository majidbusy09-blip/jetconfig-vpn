"""Controlled Bubblewrap capability test; runs only a fixed, benign self-check."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


INNER_CHECK = r"""
import json
import os
import socket
from pathlib import Path

errors = []
try:
    Path("/workspace/source.txt").write_text("must-not-work")
    errors.append("read_only_source_mount_was_writable")
except OSError:
    pass

try:
    Path("/scratch/worker.txt").write_text("scratch-ok")
except OSError:
    errors.append("scratch_mount_not_writable")

if Path(HOST_SENTINEL).exists():
    errors.append("host_sentinel_visible")

net_ns = os.stat("/proc/self/ns/net").st_ino
if net_ns == EXPECTED_NET_NS:
    errors.append("network_namespace_not_separated")

sock = socket.socket()
sock.settimeout(2)
try:
    result = sock.connect_ex(("1.1.1.1", 53))
    if result == 0:
        errors.append("outbound_network_reachable")
except OSError:
    pass
finally:
    sock.close()

print(json.dumps({"errors": errors, "net_namespace_inode": net_ns}))
"""


def build_command(bwrap: str, source: str, scratch: str, sentinel: str, expected_net_ns: int) -> list[str]:
    code = (
        INNER_CHECK.replace("HOST_SENTINEL", repr(sentinel))
        .replace("EXPECTED_NET_NS", str(expected_net_ns))
    )
    command = [
        bwrap,
        "--unshare-user", "--unshare-pid", "--unshare-net",
        "--die-with-parent", "--new-session", "--uid", "0", "--gid", "0",
        "--clearenv", "--setenv", "PATH", "/usr/bin:/bin",
        "--setenv", "HOME", "/tmp", "--setenv", "LANG", "C.UTF-8",
        "--ro-bind", "/usr", "/usr",
    ]
    for path in ("/lib", "/lib64"):
        if Path(path).exists():
            command.extend(["--ro-bind", path, path])
    command.extend([
        "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
        "--dir", "/workspace", "--dir", "/scratch",
        "--ro-bind", source, "/workspace",
        "--bind", scratch, "/scratch",
        "--chdir", "/workspace",
        "--", "/usr/bin/python3", "-S", "-c", code,
    ])
    return command


def run_probe() -> dict:
    bwrap = shutil.which("bwrap")
    if not bwrap:
        return {"status": "blocked", "passed": False, "reason": "bubblewrap_not_installed"}

    with tempfile.TemporaryDirectory(prefix="jetvpn-bwrap-probe-") as root:
        root_path = Path(root)
        source = root_path / "source"
        scratch = root_path / "scratch"
        source.mkdir()
        scratch.mkdir()
        (source / "source.txt").write_text("immutable")
        sentinel = root_path / "host-sentinel.txt"
        sentinel.write_text("host-only-secret-sentinel")
        host_net_ns = os.stat("/proc/self/ns/net").st_ino

        command = build_command(
            bwrap, str(source), str(scratch), str(sentinel), host_net_ns
        )
        try:
            completed = subprocess.run(
                command, stdin=subprocess.DEVNULL, capture_output=True,
                text=True, timeout=20, check=False,
            )
        except subprocess.TimeoutExpired:
            return {"status": "blocked", "passed": False, "reason": "bubblewrap_timeout"}
        except OSError as exc:
            return {
                "status": "blocked", "passed": False,
                "reason": "bubblewrap_launch_error", "error_type": type(exc).__name__,
            }

        try:
            payload = json.loads(completed.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            payload = None

        if completed.returncode != 0 or not isinstance(payload, dict):
            return {
                "status": "blocked", "passed": False,
                "reason": "bubblewrap_execution_failed",
                "exit_code": completed.returncode,
                "stderr_tail": completed.stderr[-2000:],
            }

        errors = payload.get("errors")
        scratch_write = (scratch / "worker.txt").is_file()
        passed = isinstance(errors, list) and not errors and scratch_write
        checks = {
            "separate_network_namespace": "pass" if "network_namespace_not_separated" not in errors else "fail",
            "source_mount_read_only": "pass" if "read_only_source_mount_was_writable" not in errors else "fail",
            "scratch_mount_writable": "pass" if scratch_write and "scratch_mount_not_writable" not in errors else "fail",
            "host_sentinel_hidden": "pass" if "host_sentinel_visible" not in errors else "fail",
            "outbound_network_denied": "pass" if "outbound_network_reachable" not in errors else "fail",
        }
        return {
            "status": "partial_isolation_checks_passed" if passed else "blocked",
            "passed": passed,
            "checks": checks,
            "errors": errors,
            "limitations": [
                "This tests only selected Bubblewrap namespace, mount, and egress properties.",
                "It does not establish seccomp filtering, cgroup resource limits, process-tree cleanup guarantees, or a complete production sandbox.",
                "Do not execute untrusted agent code on this evidence alone.",
            ],
        }


def main() -> None:
    print(json.dumps(run_probe(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
