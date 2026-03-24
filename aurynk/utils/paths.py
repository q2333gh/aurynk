import os
import tempfile
from pathlib import Path


APP_NAME = "aurynk"


def _home_dir() -> Path:
    return Path.home()


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_config_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("APPDATA")
        if base:
            return _ensure_dir(Path(base) / "Aurynk")
        return _ensure_dir(_home_dir() / "AppData" / "Roaming" / "Aurynk")

    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        return _ensure_dir(Path(xdg_config_home) / APP_NAME)
    return _ensure_dir(_home_dir() / ".config" / APP_NAME)


def get_data_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return _ensure_dir(Path(base) / "Aurynk")
        return _ensure_dir(_home_dir() / "AppData" / "Local" / "Aurynk")

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return _ensure_dir(Path(xdg_data_home) / APP_NAME)
    return _ensure_dir(_home_dir() / ".local" / "share" / APP_NAME)


def get_state_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return _ensure_dir(Path(base) / "Aurynk" / "state")
        return _ensure_dir(_home_dir() / "AppData" / "Local" / "Aurynk" / "state")

    xdg_state_home = os.environ.get("XDG_STATE_HOME")
    if xdg_state_home:
        return _ensure_dir(Path(xdg_state_home) / APP_NAME)
    return _ensure_dir(_home_dir() / ".local" / "state" / APP_NAME)


def get_runtime_dir() -> Path:
    if os.name == "nt":
        return _ensure_dir(get_state_dir() / "runtime")

    xdg_runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if xdg_runtime_dir:
        return _ensure_dir(Path(xdg_runtime_dir) / APP_NAME)
    return _ensure_dir(Path(tempfile.gettempdir()) / APP_NAME)
