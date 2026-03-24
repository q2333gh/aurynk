import os
import webbrowser
from pathlib import Path

from aurynk.api.http_api import ApiServer
from aurynk.utils.logger import get_logger

logger = get_logger("DesktopHost")


class DesktopHost:
    def __init__(self) -> None:
        project_root = Path(__file__).resolve().parent.parent
        static_dir = project_root / "web" / "dist"
        self.server = ApiServer(static_dir=static_dir if static_dir.exists() else None)

    def run(self) -> int:
        url = self.server.start()
        title = "Aurynk"

        try:
            import webview

            window = webview.create_window(title, url, width=1360, height=920, min_size=(980, 720))
            webview.start()
            return 0
        except ImportError:
            logger.warning("pywebview is not installed; opening Aurynk in the default browser")
            webbrowser.open(url)
            try:
                input("Aurynk API is running. Press Enter to stop.\n")
            except KeyboardInterrupt:
                pass
            return 0
        finally:
            self.server.stop()
