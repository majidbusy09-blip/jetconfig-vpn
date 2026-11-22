import tempfile
import unittest
from pathlib import Path

from prepare_validation_build import prepare


class PrepareValidationBuildTests(unittest.TestCase):
    def make_fixture(self, root: Path) -> None:
        (root / "lib").mkdir()
        (root / "android" / "app" / "src" / "main").mkdir(parents=True)
        (root / "lib" / "main.dart").write_text(
            "const String apkChannel = String.fromEnvironment('APK_CHANNEL', defaultValue: 'arm64');\n"
            "class Example {\n"
            "  Future<void> _checkAppUpdate({bool silent = false}) async {\n"
            "    try {\n"
            "      await doUpdate();\n"
            "    }\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )
        (root / "android" / "app" / "build.gradle").write_text(
            'android {\n  defaultConfig {\n    applicationId "com.jetconfig.vpn.jetconfig_vpn"\n  }\n}\n',
            encoding="utf-8",
        )
        (root / "android" / "app" / "src" / "main" / "AndroidManifest.xml").write_text(
            '<manifest><application android:label="jetconfig_vpn" /></manifest>\n',
            encoding="utf-8",
        )

    def test_prepares_isolated_package_and_disables_updater(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_fixture(root)
            prepare(root)
            source = (root / "lib" / "main.dart").read_text(encoding="utf-8")
            gradle = (root / "android" / "app" / "build.gradle").read_text(encoding="utf-8")
            manifest = (root / "android" / "app" / "src" / "main" / "AndroidManifest.xml").read_text(encoding="utf-8")
            self.assertIn("defaultValue: false", source)
            self.assertIn("if (isValidationBuild)", source)
            self.assertIn("com.jetconfig.vpn.jetconfig_vpn.validation", gradle)
            self.assertIn('android:label="JET VPN TEST"', manifest)

    def test_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_fixture(root)
            prepare(root)
            first = (root / "lib" / "main.dart").read_text(encoding="utf-8")
            prepare(root)
            second = (root / "lib" / "main.dart").read_text(encoding="utf-8")
            self.assertEqual(first, second)
            self.assertEqual(second.count("if (isValidationBuild)"), 1)

    def test_fails_closed_when_application_id_is_ambiguous(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_fixture(root)
            gradle_path = root / "android" / "app" / "build.gradle"
            gradle_path.write_text(
                gradle_path.read_text(encoding="utf-8") + 'applicationId "other.id"\n',
                encoding="utf-8",
            )
            with self.assertRaises(RuntimeError):
                prepare(root)


if __name__ == "__main__":
    unittest.main()
