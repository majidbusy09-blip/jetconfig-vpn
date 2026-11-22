#!/usr/bin/env python3
"""Align the disposable validation Android scaffold with production manifest/SDK requirements."""
from pathlib import Path
import re

PACKAGES = [
    "com.android.chrome", "com.chrome.beta", "com.chrome.dev",
    "com.google.android.apps.chrome", "com.android.webview",
    "com.google.android.webview", "org.telegram.messenger",
    "org.telegram.messenger.web", "org.telegram.messenger.beta",
    "org.thunderdog.challegram", "org.telegram.plus", "nekox.messenger",
    "com.instagram.android", "com.instagram.barcelona", "com.instagram.lite",
    "com.facebook.katana", "com.facebook.orca", "com.facebook.lite",
    "com.google.android.youtube", "com.google.android.apps.youtube.music",
    "com.whatsapp", "com.whatsapp.w4b", "com.twitter.android",
    "com.zhiliaoapp.musically", "com.ss.android.ugc.trill", "com.discord",
    "com.reddit.frontpage", "com.spotify.music", "com.linkedin.android",
    "com.snapchat.android", "com.openai.chatgpt", "com.google.android.gm",
    "com.google.android.apps.maps", "org.mozilla.firefox",
    "com.sec.android.app.sbrowser", "com.opera.browser", "com.brave.browser",
    "com.microsoft.emmx",
]

def align(root: Path) -> None:
    manifest_path = root / "android/app/src/main/AndroidManifest.xml"
    text = manifest_path.read_text(encoding="utf-8")
    if text.count("<manifest") != 1 or text.count("</manifest>") != 1:
        raise RuntimeError("Expected one Android manifest root")
    if "android.permission.QUERY_ALL_PACKAGES" not in text:
        text = text.replace(
            "<application",
            '    <uses-permission android:name="android.permission.QUERY_ALL_PACKAGES" />\\n    <application',
            1,
        )
    if "<queries>" not in text:
        queries = "    <queries>\\n" + "".join(
            f'        <package android:name="{p}" />\\n' for p in PACKAGES
        ) + "    </queries>\\n"
        text = text.replace("<application", queries + "    <application", 1)
    if "android.permission.QUERY_ALL_PACKAGES" not in text or "<queries>" not in text:
        raise RuntimeError("Failed to add package visibility declarations")
    manifest_path.write_text(text, encoding="utf-8")

    gradle_path = next((p for p in (
        root / "android/app/build.gradle",
        root / "android/app/build.gradle.kts",
    ) if p.is_file()), None)
    if gradle_path is None:
        raise RuntimeError("Android app Gradle file not found")
    gradle = gradle_path.read_text(encoding="utf-8")
    if gradle_path.suffix == ".kts":
        gradle = re.sub(r"(?m)^([ \\t]*compileSdk)[ \\t]*=?[ \\t]*[^\\n]+", r"\\1 = 35", gradle)
        gradle = re.sub(r"(?m)^([ \\t]*minSdk)[ \\t]*=?[ \\t]*[^\\n]+", r"\\1 = 24", gradle)
        gradle = re.sub(r"(?m)^([ \\t]*targetSdk)[ \\t]*=?[ \\t]*[^\\n]+", r"\\1 = 35", gradle)
    else:
        gradle = re.sub(r"(?m)^([ \\t]*compileSdkVersion)[ \\t]+[^\\n]+", r"\\1 35", gradle)
        gradle = re.sub(r"(?m)^([ \\t]*minSdkVersion)[ \\t]+[^\\n]+", r"\\1 24", gradle)
        gradle = re.sub(r"(?m)^([ \\t]*targetSdkVersion)[ \\t]+[^\\n]+", r"\\1 35", gradle)
    if not re.search(r"(?m)^\\s*compileSdk(?:Version)?\\s*(?:=\\s*)?35\\s*$", gradle):
        raise RuntimeError("Could not set compileSdk 35 safely")
    if not re.search(r"(?m)^\\s*minSdk(?:Version)?\\s*(?:=\\s*)?24\\s*$", gradle):
        raise RuntimeError("Could not set minSdk 24 safely")
    if not re.search(r"(?m)^\\s*targetSdk(?:Version)?\\s*(?:=\\s*)?35\\s*$", gradle):
        raise RuntimeError("Could not set targetSdk 35 safely")
    gradle_path.write_text(gradle, encoding="utf-8")
    print("VALIDATION_ANDROID_MANIFEST_PACKAGE_VISIBILITY=aligned")
    print("VALIDATION_ANDROID_SDK=compile35_min24_target35")

if __name__ == "__main__":
    align(Path.cwd())
