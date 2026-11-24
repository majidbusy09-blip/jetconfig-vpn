"""Classify whether changed repository paths require Flutter/Android validation."""

from __future__ import annotations

import os
import sys
from pathlib import PurePosixPath

APP_BUILD_PREFIXES = (
    "lib/",
    "test/",
    "android/",
    "assets/",
    "fonts/",
    "gradle/",
    "tools/v2ray_notif_patch/",
)

APP_BUILD_FILES = {
    "pubspec.yaml",
    "pubspec.lock",
    "analysis_options.yaml",
    ".github/workflows/pr-validation.yml",
}


def requires_app_build(paths: list[str]) -> bool:
    """Return true if any path can affect app behavior, analysis, or APK output."""
    for raw_path in paths:
        path = raw_path.strip().replace("\\", "/")
        if not path:
            continue
        if path in APP_BUILD_FILES or path.startswith(APP_BUILD_PREFIXES):
            return True
        if "/" not in path and (
            path.endswith(".gradle") or path.endswith(".gradle.kts")
        ):
            return True
    return False


def main() -> int:
    paths = [line.rstrip("\\n") for line in sys.stdin]
    app_build = requires_app_build(paths)
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"app_build={'true' if app_build else 'false'}\\n")
    print(
        "Application/build-affecting changes detected."
        if app_build
        else "Tooling/documentation-only changes detected; Flutter/APK build can be skipped."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
