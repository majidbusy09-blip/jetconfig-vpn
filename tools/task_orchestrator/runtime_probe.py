"""Read-only inventory of CI isolation prerequisites; never launches a runtime."""
from __future__ import annotations

import json
import os
import platform
import shutil
from pathlib import Path, PurePosixPath


RUNTIME_TOOLS = ("docker", "podman", "nerdctl", "bwrap", "unshare")
CGROUP_LIMIT_FILES = ("cpu.max", "memory.max", "pids.max")


def _read(path: str | Path) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return None


def build_cgroup_report(
    *, cgroup_root: str, process_cgroup: str | None,
) -> dict:
    """Inspect the current cgroup v2 location without changing host state."""
    result = {
        "process_path": None,
        "directory_visible": False,
        "directory_writable": False,
        "controllers": [],
        "subtree_control": None,
        "limits": {name: None for name in CGROUP_LIMIT_FILES},
        "delegation_candidate": False,
    }
    if not process_cgroup:
        return result

    relative = None
    for line in process_cgroup.splitlines():
        fields = line.split(":", 2)
        if len(fields) == 3 and fields[0] == "0" and fields[1] == "":
            relative = fields[2]
            break
    if relative is None:
        return result

    candidate = PurePosixPath(relative)
    if candidate.is_absolute():
        candidate = PurePosixPath(*candidate.parts[1:])
    if any(part in ("", ".", "..") for part in candidate.parts):
        return result

    root = Path(cgroup_root).resolve()
    directory = (root / Path(*candidate.parts)).resolve()
    try:
        directory.relative_to(root)
    except ValueError:
        return result

    result["process_path"] = "/" + str(candidate)
    result["directory_visible"] = directory.is_dir()
    if not result["directory_visible"]:
        return result

    result["directory_writable"] = os.access(directory, os.W_OK | os.X_OK)
    controllers = _read(directory / "cgroup.controllers")
    result["controllers"] = controllers.split() if controllers else []
    result["subtree_control"] = _read(directory / "cgroup.subtree_control")
    result["limits"] = {
        name: _read(directory / name) for name in CGROUP_LIMIT_FILES
    }
    result["delegation_candidate"] = bool(
        result["directory_writable"]
        and {"cpu", "memory", "pids"}.issubset(result["controllers"])
    )
    return result


def build_report(
    *,
    tool_paths: dict[str, str | None],
    effective_uid: int | None,
    kernel_release: str,
    proc_status: str | None,
    namespace_names: list[str],
    cgroup_controllers: str | None,
    userns_max: str | None,
    unprivileged_userns_clone: str | None,
    docker_socket_present: bool,
    cgroup_report: dict | None = None,
) -> dict:
    seccomp_mode = None
    if proc_status:
        for line in proc_status.splitlines():
            if line.startswith("Seccomp:"):
                try:
                    seccomp_mode = int(line.split(":", 1)[1].strip())
                except ValueError:
                    pass

    controllers = cgroup_controllers.split() if cgroup_controllers else []
    return {
        "schema_version": 1,
        "classification": "inventory_only_not_sandbox",
        "eligible_for_untrusted_agent_execution": False,
        "host": {
            "os": platform.system(),
            "kernel_release": kernel_release,
            "effective_uid": effective_uid,
            "running_as_non_root": effective_uid is not None and effective_uid != 0,
        },
        "runtime_tool_paths": {name: tool_paths.get(name) for name in RUNTIME_TOOLS},
        "docker_socket_present": docker_socket_present,
        "namespaces_visible": sorted(namespace_names),
        "seccomp_mode": seccomp_mode,
        "cgroup_v2_available": cgroup_controllers is not None,
        "cgroup_controllers": controllers,
        "cgroup_current_process": cgroup_report or {
            "delegation_candidate": False,
            "reason": "not_inspected",
        },
        "user_namespace": {
            "max_user_namespaces": userns_max,
            "unprivileged_userns_clone": unprivileged_userns_clone,
        },
        "limitations": [
            "This report checks discoverability and host metadata only.",
            "Cgroup visibility and write-access indicators do not prove enforceable resource limits or delegated child-cgroup creation.",
            "It does not prove rootless operation, mount isolation, network denial, resource enforcement, or cleanup.",
            "A Docker socket or daemon must never be exposed to an untrusted coding agent.",
            "No runtime was launched and no isolation boundary was tested by this inventory.",
        ],
    }


def collect_report() -> dict:
    namespace_dir = Path("/proc/self/ns")
    try:
        namespaces = [entry.name for entry in namespace_dir.iterdir()]
    except OSError:
        namespaces = []

    uid = os.geteuid() if hasattr(os, "geteuid") else None
    cgroup_report = build_cgroup_report(
        cgroup_root="/sys/fs/cgroup",
        process_cgroup=_read("/proc/self/cgroup"),
    )
    return build_report(
        tool_paths={name: shutil.which(name) for name in RUNTIME_TOOLS},
        effective_uid=uid,
        kernel_release=platform.release(),
        proc_status=_read("/proc/self/status"),
        namespace_names=namespaces,
        cgroup_controllers=_read("/sys/fs/cgroup/cgroup.controllers"),
        userns_max=_read("/proc/sys/user/max_user_namespaces"),
        unprivileged_userns_clone=_read("/proc/sys/kernel/unprivileged_userns_clone"),
        docker_socket_present=Path("/var/run/docker.sock").exists(),
        cgroup_report=cgroup_report,
    )


def main() -> None:
    print(json.dumps(collect_report(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
