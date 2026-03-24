import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Optional

from aurynk.utils.logger import get_logger

logger = get_logger("SystemIntegration")


class NoopTrayIntegration:
    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None


class SystemIntegration:
    def open_path(self, target: str) -> bool:
        try:
            path = Path(target).expanduser()
            if os.name == "nt":
                os.startfile(str(path))  # type: ignore[attr-defined]
                return True
            if sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
                return True
            subprocess.Popen(["xdg-open", str(path)])
            return True
        except Exception as exc:
            logger.error("Failed to open path %s: %s", target, exc)
            return False

    def open_url(self, target: str) -> bool:
        try:
            return webbrowser.open(target)
        except Exception as exc:
            logger.error("Failed to open url %s: %s", target, exc)
            return False

    def notify(self, title: str, body: str = "") -> None:
        try:
            from aurynk.utils.notify import show_notification

            show_notification(title, body)
        except Exception:
            logger.info("[Notification] %s: %s", title, body)

    def quit(self) -> None:
        return None

    def minimize(self) -> None:
        return None
