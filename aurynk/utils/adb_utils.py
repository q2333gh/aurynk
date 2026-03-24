import os
import shutil


def _is_executable(path: str) -> bool:
    return bool(path) and os.path.isfile(path) and os.access(path, os.X_OK)


def _candidate_paths() -> list[str]:
    candidates: list[str] = []
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        user_profile = os.environ.get("USERPROFILE", "")
        android_home = os.environ.get("ANDROID_HOME", "")
        android_sdk_root = os.environ.get("ANDROID_SDK_ROOT", "")
        candidates.extend(
            [
                os.path.join(local_app_data, "Android", "Sdk", "platform-tools", "adb.exe"),
                os.path.join(user_profile, "AppData", "Local", "Android", "Sdk", "platform-tools", "adb.exe"),
                os.path.join(android_home, "platform-tools", "adb.exe"),
                os.path.join(android_sdk_root, "platform-tools", "adb.exe"),
            ]
        )
    return [path for path in candidates if path]


def resolve_adb_path(raise_on_missing: bool = False) -> str:
    """Resolve ADB from settings, PATH, or common SDK locations."""
    configured_path = ""
    try:
        from aurynk.utils.settings import SettingsManager

        settings = SettingsManager()
        configured_path = settings.get("adb", "adb_path", "").strip()
        if _is_executable(configured_path):
            return configured_path
    except Exception:
        configured_path = ""

    resolved = shutil.which("adb")
    if resolved:
        return resolved

    for candidate in _candidate_paths():
        if _is_executable(candidate):
            return candidate

    if raise_on_missing:
        if configured_path:
            raise FileNotFoundError(
                f"Configured adb_path does not exist or is not executable: {configured_path}"
            )
        raise FileNotFoundError(
            "ADB executable not found. Install Android platform-tools or set adb.adb_path in Settings."
        )

    return configured_path or "adb"


def get_adb_path():
    """Return the best-known ADB path or the fallback command name."""
    return resolve_adb_path(raise_on_missing=False)


def is_device_connected(address, connect_port):
    """Check if a device is connected via adb."""
    import subprocess

    serial = f"{address}:{connect_port}"
    from aurynk.utils.adb_utils import get_adb_path

    try:
        result = subprocess.run([get_adb_path(), "devices"], capture_output=True, text=True)
        if result.returncode != 0:
            return False
        for line in result.stdout.splitlines():
            # Must have tab separator and "device" status (not "offline" or other states)
            if serial in line and "\tdevice" in line:
                return True
        return False
    except Exception:
        return False


def clear_device_notifications(serial: str) -> bool:
    """Clear all Aurynk notifications from the Android device.

    Args:
        serial: Device serial (address:port for wireless, or USB serial)

    Returns:
        True if cleared successfully, False otherwise
    """
    import subprocess

    try:
        # Cancel notification with our specific tag
        cancel_cmd = "cmd notification cancel aurynk_status"
        subprocess.run(
            [get_adb_path(), "-s", serial, "shell", cancel_cmd], capture_output=True, timeout=2
        )
        return True
    except Exception:
        return False


def send_device_notification(serial: str, message: str, title: str = "Aurynk") -> bool:
    """Send a notification/toast to the Android device via ADB.

    Args:
        serial: Device serial (address:port for wireless, or USB serial)
        message: Notification message to display
        title: Notification title (default: "Aurynk")

    Returns:
        True if notification was sent successfully, False otherwise
    """
    import subprocess

    try:
        # Clear old notifications first
        clear_device_notifications(serial)

        # Post a system notification using cmd notification
        # Format: cmd notification post [flags] <tag> <text>
        # Need to properly escape the message for shell parsing
        import shlex

        # Build the notification command with proper quoting
        notification_cmd = f"cmd notification post -S bigtext -t {shlex.quote(title)} aurynk_status {shlex.quote(message)}"

        cmd = [get_adb_path(), "-s", serial, "shell", notification_cmd]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)

        # Also log to logcat for debugging
        subprocess.run(
            [get_adb_path(), "-s", serial, "shell", "log", "-t", "Aurynk", message], timeout=2
        )

        return result.returncode == 0
    except Exception:
        return False
