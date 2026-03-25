import logging
import logging.handlers
import os
import sys
import threading
from pathlib import Path

from aurynk.utils.paths import get_state_dir

# Ensure directory exists
try:
    LOG_DIR = str(get_state_dir())
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
    LOG_FILE = str(Path(LOG_DIR) / "aurynk.log")
except Exception:
    # Fallback to temp dir if we can't create the state dir
    import tempfile

    LOG_DIR = tempfile.gettempdir()
    LOG_FILE = os.path.join(LOG_DIR, "aurynk.log")


_HANDLER_LOCK = threading.Lock()
_FORMATTER: logging.Formatter | None = None
_CONSOLE_HANDLER: logging.Handler | None = None
_FILE_HANDLER: logging.Handler | None = None


def _get_formatter() -> logging.Formatter:
    global _FORMATTER
    if _FORMATTER is None:
        _FORMATTER = logging.Formatter(
            "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    return _FORMATTER


def _get_console_handler() -> logging.Handler:
    global _CONSOLE_HANDLER
    if _CONSOLE_HANDLER is None:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(_get_formatter())
        _CONSOLE_HANDLER = handler
    return _CONSOLE_HANDLER


def _get_file_handler() -> logging.Handler | None:
    global _FILE_HANDLER
    if _FILE_HANDLER is None:
        try:
            handler = logging.handlers.RotatingFileHandler(
                LOG_FILE,
                maxBytes=1024 * 1024,
                backupCount=3,
                encoding="utf-8",
                delay=True,
            )
            handler.setLevel(logging.DEBUG)
            handler.setFormatter(_get_formatter())
            _FILE_HANDLER = handler
        except Exception as exc:
            print(f"Failed to setup file logging: {exc}", file=sys.stderr)
            _FILE_HANDLER = None
    return _FILE_HANDLER


def get_logger(name):
    """Get a configured logger instance."""
    logger = logging.getLogger(name)

    # Only configure if handlers haven't been added yet
    if not logger.handlers:
        with _HANDLER_LOCK:
            logger.setLevel(logging.DEBUG)
            logger.propagate = False

            console_handler = _get_console_handler()
            if console_handler not in logger.handlers:
                logger.addHandler(console_handler)

            file_handler = _get_file_handler()
            if file_handler and file_handler not in logger.handlers:
                logger.addHandler(file_handler)

    return logger
