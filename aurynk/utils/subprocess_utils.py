import os
import subprocess
from typing import Any


def _windows_no_console_kwargs() -> dict[str, Any]:
    if os.name != "nt":
        return {}

    kwargs: dict[str, Any] = {}
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if creationflags:
        kwargs["creationflags"] = creationflags

    startupinfo_factory = getattr(subprocess, "STARTUPINFO", None)
    if startupinfo_factory is not None:
        startupinfo = startupinfo_factory()
        startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 0)
        startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
        kwargs["startupinfo"] = startupinfo

    return kwargs


def run_subprocess(*args, **kwargs):
    merged = _windows_no_console_kwargs()
    merged.update(kwargs)
    return subprocess.run(*args, **merged)


def popen_subprocess(*args, **kwargs):
    merged = _windows_no_console_kwargs()
    merged.update(kwargs)
    return subprocess.Popen(*args, **merged)
