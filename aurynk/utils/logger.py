import logging
import logging.handlers
import sys
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


def get_logger(name):
    """Get a configured logger instance."""
    logger = logging.getLogger(name)

    # Only configure if handlers haven't been added yet
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        # Formatter
        formatter = logging.Formatter(
            "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler (Rotating)
        try:
            # 1MB max size, keep 3 backups
            file_handler = logging.handlers.RotatingFileHandler(
                LOG_FILE, maxBytes=1024 * 1024, backupCount=3, encoding="utf-8"
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            # Fallback if we can't write to file
            print(f"Failed to setup file logging: {e}", file=sys.stderr)

    return logger
