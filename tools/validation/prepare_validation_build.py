#!/usr/bin/env python3
"""Prepare a safe, side-by-side JET VPN validation build in CI only.

This script runs only in the disposable GitHub Actions workspace. It never
changes the production Android package identity or production release workflow.
"""
from __future__ import annotations

import re
from pathlib import Path


APP_ID = "com.jetconfig.vpn.jetconfig_vpn"
VALIDATION_APP_ID = APP_ID + ".validation"
APP_LABEL = "JET VPN TEST"


def _replace_once(text: str, pattern: re.Pattern[str], replacement: str, label: str) -> str:
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one {label}; found {len(matches)}")
    return pattern.sub(replacement, text, count=1)


def prepare(root: Path) -> None:
    main_path = root / "lib" / "main.dart"
    source = main_path.read_text(encoding="utf-8")

    define_anchor = "const String apkChannel = String.fromEnvironment('APK_CHANNEL', defaultValue: 'arm64');"
    validation_define = (
        "const bool isValidationBuild = "
        "bool.fromEnvironment('JETVPN_VALIDATION_BUILD', defaultValue: false);"
    )
    if validation_define not in source:
        if source.count(define_anchor) != 1:
            raise RuntimeError("Could not uniquely locate APK_CHANNEL declaration")
        source = source.replace(define_anchor, define_anchor + "\n" + validation_define, 1)

    method_anchor = "  Future<void> _checkAppUpdate({bool silent = false}) async {\n    try {"
    validation_guard = (
        "  Future<void> _checkAppUpdate({bool silent = false}) async {\n"
        "    if (isValidationBuild) {\n"
        "      if (!silent && mounted) {\n"
        "        _showToast('در نسخه آزمایشی، بررسی بروزرسانی غیرفعال است');\n"
        "      }\n"
        "      return;\n"
        "    }\n"
        "    try {"
    )
    if "if (isValidationBuild)" not in source:
        if source.count(method_anchor) != 1:
            raise RuntimeError("Could not uniquely locate app update method")
        source = source.replace(method_anchor, validation_guard, 1)
    main_path.write_text(source, encoding="utf-8")

    gradle_paths = [root / "android" / "app" / "build.gradle", root / "android" / "app" / "build.gradle.kts"]
    gradle_path = next((p for p in gradle_paths if p.is_file()), None)
    if gradle_path is None:
        raise RuntimeError("Generated Android app Gradle file was not found")
    gradle = gradle_path.read_text(encoding="utf-8")
    app_id_pattern = re.compile(r"(^[ \\t]*applicationId[ \\t]*=?[ \\t]*)(['\"])([^'\"]+)(['\"])", re.MULTILINE)
    matches = list(app_id_pattern.finditer(gradle))
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one applicationId; found {len(matches)}")
    current_id = matches[0].group(3)
    if current_id == APP_ID:
        gradle = app_id_pattern.sub(lambda m: m.group(1) + m.group(2) + VALIDATION_APP_ID + m.group(4), gradle, count=1)
    elif current_id != VALIDATION_APP_ID:
        raise RuntimeError(f"Unexpected generated applicationId: {current_id}")
    gradle_path.write_text(gradle, encoding="utf-8")

    manifest_path = root / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
    manifest = manifest_path.read_text(encoding="utf-8")
    label_pattern = re.compile(r'android:label="[^"]+"')
    if 'android:label="JET VPN TEST"' not in manifest:
        manifest = _replace_once(manifest, label_pattern, 'android:label="JET VPN TEST"', "manifest app label")
    manifest_path.write_text(manifest, encoding="utf-8")

    print(f"VALIDATION_APPLICATION_ID={VALIDATION_APP_ID}")
    print(f"VALIDATION_APP_LABEL={APP_LABEL}")
    print("VALIDATION_UPDATER_DISABLED=true")


if __name__ == "__main__":
    prepare(Path.cwd())
