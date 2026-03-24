import os
import sys
import webbrowser
from pathlib import Path

from aurynk.api.http_api import ApiServer
from aurynk.utils.logger import get_logger

logger = get_logger("DesktopHost")


def _candidate_app_roots() -> list[Path]:
    roots: list[Path] = []

    if hasattr(sys, "_MEIPASS"):
        roots.append(Path(sys._MEIPASS))

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        roots.append(exe_dir)
        roots.append(exe_dir / "_internal")

    roots.append(Path(__file__).resolve().parent.parent)
    roots.append(Path.cwd().resolve())

    unique_roots: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        unique_roots.append(root)
    return unique_roots


def _resolve_static_dir() -> Path | None:
    for root in _candidate_app_roots():
        candidate = root / "web" / "dist"
        if candidate.exists():
            return candidate
    return None


class DesktopHost:
    def __init__(self) -> None:
        static_dir = _resolve_static_dir()
        self.server = ApiServer(static_dir=static_dir)

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
