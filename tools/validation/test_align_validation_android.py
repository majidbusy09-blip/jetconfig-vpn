import tempfile
import unittest
from pathlib import Path
from align_validation_android import align

class AlignValidationAndroidTests(unittest.TestCase):
    def fixture(self, root, kts=False):
        manifest = root / "android/app/src/main/AndroidManifest.xml"
        manifest.parent.mkdir(parents=True)
        manifest.write_text('<manifest xmlns:android="http://schemas.android.com/apk/res/android"><application android:label="JET VPN TEST" /></manifest>', encoding="utf-8")
        gradle = root / ("android/app/build.gradle.kts" if kts else "android/app/build.gradle")
        gradle.parent.mkdir(parents=True, exist_ok=True)
        if kts:
            gradle.write_text('android {\\n    compileSdk = 34\\n    defaultConfig {\\n        minSdk = 23\\n        targetSdk = 34\\n    }\\n}\\n', encoding="utf-8")
        else:
            gradle.write_text('android {\\n    compileSdkVersion 34\\n    defaultConfig {\\n        minSdkVersion 23\\n        targetSdkVersion 34\\n    }\\n}\\n', encoding="utf-8")
    def test_aligns_manifest_and_groovy_gradle(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.fixture(root); align(root)
            m=(root/"android/app/src/main/AndroidManifest.xml").read_text()
            g=(root/"android/app/build.gradle").read_text()
            self.assertIn("QUERY_ALL_PACKAGES",m); self.assertIn("org.telegram.messenger",m)
            self.assertIn("compileSdkVersion 35",g); self.assertIn("minSdkVersion 24",g); self.assertIn("targetSdkVersion 35",g)
    def test_aligns_kotlin_gradle(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.fixture(root,True); align(root)
            g=(root/"android/app/build.gradle.kts").read_text()
            self.assertIn("compileSdk = 35",g); self.assertIn("minSdk = 24",g); self.assertIn("targetSdk = 35",g)
    def test_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.fixture(root); align(root)
            m=(root/"android/app/src/main/AndroidManifest.xml").read_text()
            align(root)
            self.assertEqual(m,(root/"android/app/src/main/AndroidManifest.xml").read_text())

if __name__ == "__main__":
    unittest.main()
