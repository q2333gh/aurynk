import gettext
import os
import sys

from aurynk.desktop_host import DesktopHost
from aurynk.utils.logger import get_logger
from aurynk.utils.paths import get_runtime_dir

gettext.install("aurynk", localedir=os.path.join(os.path.dirname(__file__), "..", "po"))

logger = get_logger("Launcher")


def _cleanup_runtime_files() -> None:
    runtime_dir = get_runtime_dir()
    for filename in ("aurynk_app.sock", "aurynk_tray.sock"):
        path = runtime_dir / filename
        if path.exists():
            try:
                path.unlink()
            except Exception:
                logger.debug("Failed to remove runtime file %s", path, exc_info=True)


def _run_legacy_gtk(argv: list[str]) -> int:
    from aurynk.application import main as gtk_main

    return gtk_main(argv)


def main(argv=None) -> int:
    argv = argv or sys.argv
    ui_mode = os.environ.get("AURYNK_UI", "auto").lower()

    if ui_mode == "gtk":
        return _run_legacy_gtk(argv)

    if ui_mode == "web":
        return DesktopHost().run()

    if os.name == "nt":
        return DesktopHost().run()

    try:
        import webview  # noqa: F401

        return DesktopHost().run()
    except Exception:
        logger.info("pywebview unavailable, falling back to legacy GTK host")
        return _run_legacy_gtk(argv)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        _cleanup_runtime_files()
        sys.exit(0)
