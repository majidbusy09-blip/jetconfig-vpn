#!/usr/bin/env python3
"""Align the disposable validation Android scaffold with production requirements."""
from pathlib import Path
import re

# Keep this list byte-for-byte aligned with the production build workflow.
PACKAGES = """com.android.chrome com.chrome.beta com.google.android.apps.chrome
com.android.webview com.google.android.webview org.telegram.messenger
org.telegram.messenger.web org.telegram.messenger.beta org.thunderdog.challegram
com.instagram.android com.instagram.barcelona com.whatsapp
com.google.android.youtube com.twitter.android org.mozilla.firefox
com.sec.android.app.sbrowser com.opera.browser com.brave.browser
com.microsoft.emmx com.facebook.katana com.facebook.orca
com.zhiliaoapp.musically com.discord""".split()


def _set_sdk(text: str, key: str, value: int, groovy_key: str) -> str:
    patterns = [
        (re.compile(rf"(?m)^(\s*){re.escape(key)}\s*=\s*[^\n]+$"), rf"\g<1>{key} = {value}"),
        (re.compile(rf"(?m)^(\s*){re.escape(groovy_key)}\s+[^\n]+$"), rf"\g<1>{groovy_key} {value}"),
        (re.compile(rf"(?m)^(\s*){re.escape(key)}\s+\d+\s*$"), rf"\g<1>{key} {value}"),
    ]
    for pattern, replacement in patterns:
        matches = list(pattern.finditer(text))
        if matches:
            if len(matches) != 1:
                raise RuntimeError(f"Expected one {key} declaration; found {len(matches)}")
            return pattern.sub(replacement, text, count=1)
    raise RuntimeError(f"Could not find {key} declaration in generated Gradle file")


def align(root: Path) -> None:
    manifest_path = root / "android/app/src/main/AndroidManifest.xml"
    manifest = manifest_path.read_text(encoding="utf-8")
    if manifest.count("<manifest") != 1 or manifest.count("</manifest>") != 1:
        raise RuntimeError("Expected one Android manifest root")

    if "android.permission.QUERY_ALL_PACKAGES" not in manifest:
        manifest = manifest.replace(
            "<application",
            '    <uses-permission android:name="android.permission.QUERY_ALL_PACKAGES" />\n    <application',
            1,
        )

    if "<queries>" not in manifest:
        queries = '    <queries>\n'
        queries += "".join(f'        <package android:name="{p}" />\n' for p in PACKAGES)
        queries += (
            '        <intent>\n'
            '            <action android:name="android.intent.action.MAIN" />\n'
            '            <category android:name="android.intent.category.LAUNCHER" />\n'
            '        </intent>\n'
            '    </queries>\n'
        )
        manifest = manifest.replace("<application", queries + "    <application", 1)

    if "android.permission.QUERY_ALL_PACKAGES" not in manifest or "<queries>" not in manifest:
        raise RuntimeError("Failed to add production package visibility declarations")
    manifest_path.write_text(manifest, encoding="utf-8")

    gradle_path = next((p for p in (
        root / "android/app/build.gradle",
        root / "android/app/build.gradle.kts",
    ) if p.is_file()), None)
    if gradle_path is None:
        raise RuntimeError("Android app Gradle file not found")

    gradle = gradle_path.read_text(encoding="utf-8")
    gradle = _set_sdk(gradle, "compileSdk", 35, "compileSdkVersion")
    gradle = _set_sdk(gradle, "minSdk", 24, "minSdkVersion")
    gradle = _set_sdk(gradle, "targetSdk", 35, "targetSdkVersion")
    gradle_path.write_text(gradle, encoding="utf-8")
    print("VALIDATION_ANDROID_MANIFEST_PACKAGE_VISIBILITY=production-aligned")
    print("VALIDATION_ANDROID_SDK=compile35_min24_target35")


if __name__ == "__main__":
    align(Path.cwd())
