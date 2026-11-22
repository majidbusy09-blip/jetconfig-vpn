import tempfile
import unittest
from pathlib import Path

from align_validation_android import PACKAGES, align


class AlignValidationAndroidTests(unittest.TestCase):
    def fixture(self, root: Path, kts: bool = False) -> None:
        manifest = root / "android/app/src/main/AndroidManifest.xml"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(
            '<manifest xmlns:android="http://schemas.android.com/apk/res/android">'
            '<application android:label="JET VPN TEST" /></manifest>',
            encoding="utf-8",
        )
        gradle = root / ("android/app/build.gradle.kts" if kts else "android/app/build.gradle")
        gradle.parent.mkdir(parents=True, exist_ok=True)
        if kts:
            content = (
                "android {\n"
                "    compileSdk = 34\n"
                "    defaultConfig {\n"
                "        minSdk = 23\n"
                "        targetSdk = 34\n"
                "    }\n"
                "}\n"
            )
        else:
            content = (
                "android {\n"
                "    compileSdkVersion 34\n"
                "    defaultConfig {\n"
                "        minSdkVersion 23\n"
                "        targetSdkVersion 34\n"
                "    }\n"
                "}\n"
            )
        gradle.write_text(content, encoding="utf-8")

    def assert_manifest_aligned(self, manifest: str) -> None:
        self.assertIn("QUERY_ALL_PACKAGES", manifest)
        self.assertIn("<queries>", manifest)
        self.assertIn("android.intent.action.MAIN", manifest)
        self.assertIn("android.intent.category.LAUNCHER", manifest)
        for package in PACKAGES:
            self.assertIn(f'android:name="{package}"', manifest)

    def test_aligns_manifest_and_groovy_gradle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            align(root)
            manifest = (root / "android/app/src/main/AndroidManifest.xml").read_text()
            gradle = (root / "android/app/build.gradle").read_text()
            self.assert_manifest_aligned(manifest)
            self.assertIn("compileSdkVersion 35", gradle)
            self.assertIn("minSdkVersion 24", gradle)
            self.assertIn("targetSdkVersion 35", gradle)

    def test_aligns_kotlin_gradle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, True)
            align(root)
            gradle = (root / "android/app/build.gradle.kts").read_text()
            self.assertIn("compileSdk = 35", gradle)
            self.assertIn("minSdk = 24", gradle)
            self.assertIn("targetSdk = 35", gradle)

    def test_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            align(root)
            manifest_path = root / "android/app/src/main/AndroidManifest.xml"
            first = manifest_path.read_text()
            align(root)
            self.assertEqual(first, manifest_path.read_text())


if __name__ == "__main__":
    unittest.main()
