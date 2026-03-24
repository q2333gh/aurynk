import tempfile
import unittest
from unittest.mock import patch

from aurynk.utils import paths


class TestPaths(unittest.TestCase):
    def test_windows_config_dir_uses_appdata(self):
        with tempfile.TemporaryDirectory() as tempdir:
            with patch("aurynk.utils.paths.os.name", "nt"):
                with patch.dict("os.environ", {"APPDATA": tempdir}, clear=True):
                    config_dir = paths.get_config_dir()
        self.assertEqual(config_dir.name, "Aurynk")
        self.assertIn(tempdir, str(config_dir))

    def test_runtime_dir_on_windows_uses_state_runtime(self):
        with tempfile.TemporaryDirectory() as tempdir:
            with patch("aurynk.utils.paths.os.name", "nt"):
                with patch.dict("os.environ", {"LOCALAPPDATA": tempdir}, clear=True):
                    runtime_dir = paths.get_runtime_dir()
        self.assertTrue(str(runtime_dir).endswith("Aurynk\\state\\runtime"))


if __name__ == "__main__":
    unittest.main()
