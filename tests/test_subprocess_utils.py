import unittest
from unittest.mock import MagicMock, patch

from aurynk.utils import subprocess_utils


class TestSubprocessUtils(unittest.TestCase):
    @patch("aurynk.utils.subprocess_utils.os.name", "nt")
    @patch("aurynk.utils.subprocess_utils.subprocess.run")
    def test_run_subprocess_hides_console_on_windows(self, mock_run):
        with patch.object(
            subprocess_utils.subprocess,
            "STARTUPINFO",
            return_value=MagicMock(dwFlags=0, wShowWindow=0),
        ):
            subprocess_utils.run_subprocess(["adb", "devices"])

        kwargs = mock_run.call_args.kwargs
        self.assertIn("creationflags", kwargs)
        self.assertIn("startupinfo", kwargs)

    @patch("aurynk.utils.subprocess_utils.os.name", "nt")
    @patch("aurynk.utils.subprocess_utils.subprocess.Popen")
    def test_popen_subprocess_hides_console_on_windows(self, mock_popen):
        with patch.object(
            subprocess_utils.subprocess,
            "STARTUPINFO",
            return_value=MagicMock(dwFlags=0, wShowWindow=0),
        ):
            subprocess_utils.popen_subprocess(["scrcpy"])

        kwargs = mock_popen.call_args.kwargs
        self.assertIn("creationflags", kwargs)
        self.assertIn("startupinfo", kwargs)


if __name__ == "__main__":
    unittest.main()
