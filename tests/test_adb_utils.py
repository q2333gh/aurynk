import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aurynk.utils import adb_utils


class _FakeSettings:
    def __init__(self, values):
        self.values = values

    def get(self, category, key, default=None):
        return self.values.get((category, key), default)


class TestExecutableResolution(unittest.TestCase):
    def _make_tool(self, root: Path, relative_path: str) -> str:
        tool_path = root / relative_path
        tool_path.parent.mkdir(parents=True, exist_ok=True)
        tool_path.write_text("stub", encoding="utf-8")
        return str(tool_path)

    @patch("aurynk.utils.adb_utils._is_executable", side_effect=lambda path: Path(path).is_file())
    @patch("aurynk.utils.adb_utils._candidate_paths", return_value=[])
    @patch("aurynk.utils.adb_utils.shutil.which", return_value=None)
    def test_resolve_adb_path_from_configured_directory(
        self, _mock_which, _mock_candidates, _mock_is_executable
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            tool = self._make_tool(Path(tempdir), "platform-tools/adb.exe")
            values = {("adb", "adb_path"): tempdir}

            with patch("aurynk.utils.settings.SettingsManager", return_value=_FakeSettings(values)):
                resolved = adb_utils.resolve_adb_path()

        self.assertEqual(resolved, tool)

    @patch("aurynk.utils.adb_utils._is_executable", side_effect=lambda path: Path(path).is_file())
    @patch("aurynk.utils.adb_utils._candidate_paths", return_value=[])
    @patch("aurynk.utils.adb_utils.shutil.which", return_value=None)
    def test_resolve_adb_path_uses_portable_root_after_normal_lookup_fails(
        self, _mock_which, _mock_candidates, _mock_is_executable
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            tool = self._make_tool(Path(tempdir), "tools/adb/adb.exe")
            values = {("adb", "adb_path"): ""}

            with patch("aurynk.utils.settings.SettingsManager", return_value=_FakeSettings(values)):
                with patch("aurynk.utils.adb_utils._portable_roots", return_value=[Path(tempdir)]):
                    resolved = adb_utils.resolve_adb_path()

        self.assertEqual(resolved, tool)

    @patch("aurynk.utils.adb_utils._is_executable", side_effect=lambda path: Path(path).is_file())
    @patch("aurynk.utils.adb_utils._candidate_paths", return_value=[])
    def test_resolve_adb_path_keeps_path_priority_over_portable_bundle(
        self, _mock_candidates, _mock_is_executable
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            self._make_tool(Path(tempdir), "tools/adb/adb.exe")
            values = {("adb", "adb_path"): ""}

            with patch("aurynk.utils.settings.SettingsManager", return_value=_FakeSettings(values)):
                with patch("aurynk.utils.adb_utils._portable_roots", return_value=[Path(tempdir)]):
                    with patch("aurynk.utils.adb_utils.shutil.which", return_value="C:/sdk/adb.exe"):
                        resolved = adb_utils.resolve_adb_path()

        self.assertEqual(resolved, "C:/sdk/adb.exe")

    @patch("aurynk.utils.adb_utils._is_executable", side_effect=lambda path: Path(path).is_file())
    @patch("aurynk.utils.adb_utils.shutil.which", return_value=None)
    def test_resolve_scrcpy_path_from_configured_directory(self, _mock_which, _mock_is_executable):
        with tempfile.TemporaryDirectory() as tempdir:
            tool = self._make_tool(Path(tempdir), "scrcpy/scrcpy.exe")
            values = {("scrcpy", "scrcpy_path"): tempdir}

            with patch("aurynk.utils.settings.SettingsManager", return_value=_FakeSettings(values)):
                resolved = adb_utils.resolve_scrcpy_path()

        self.assertEqual(resolved, tool)

    @patch("aurynk.utils.adb_utils._is_executable", side_effect=lambda path: Path(path).is_file())
    @patch("aurynk.utils.adb_utils.shutil.which", return_value=None)
    def test_resolve_scrcpy_path_uses_portable_root(self, _mock_which, _mock_is_executable):
        with tempfile.TemporaryDirectory() as tempdir:
            tool = self._make_tool(Path(tempdir), "tools/scrcpy/scrcpy.exe")
            values = {("scrcpy", "scrcpy_path"): ""}

            with patch("aurynk.utils.settings.SettingsManager", return_value=_FakeSettings(values)):
                with patch("aurynk.utils.adb_utils._portable_roots", return_value=[Path(tempdir)]):
                    resolved = adb_utils.resolve_scrcpy_path()

        self.assertEqual(resolved, tool)


if __name__ == "__main__":
    unittest.main()
