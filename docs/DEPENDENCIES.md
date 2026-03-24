# Dependency Guide

This document is the source-of-truth for getting Aurynk running from source.

The recommended path is Windows-first and based on the commands already validated in a real setup:

- `winget` for system tools
- `uv` for Python installation and virtual environments
- `npm` for the web frontend build
- `python -m aurynk` for launch

## Dependency Matrix

| Dependency | Required | Why Aurynk needs it | How to install on Windows |
| --- | --- | --- | --- |
| Python 3.12 | Yes | Runs the backend and desktop host | `winget install --id=astral-sh.uv -e` then `uv python install 3.12` |
| `uv` | Recommended | Creates and manages the project virtual environment | `winget install --id=astral-sh.uv -e` |
| Node.js + npm | Yes for source builds | Builds `web/dist` for the desktop UI | Install Node.js LTS from your usual package manager |
| `adb` | Yes | Pairing, connect, disconnect, screenshots, device queries | `winget install --id=Google.PlatformTools -e` |
| `scrcpy` | Yes for mirroring | Powers the `Mirror` action | `winget install --id=Genymobile.scrcpy -e` |
| `pillow` | Yes | Provides the `PIL` module used by QR and image handling | Installed by `pip install -e ".[dev]"` |
| `pywebview` | Yes | Hosts the desktop UI window on Windows | Installed by `pip install -e ".[dev]"` |
| `qrcode` | Yes for QR pairing | Generates the pairing QR code | Installed by `pip install -e ".[dev]"` |
| `zeroconf` | Yes for QR pairing and wireless discovery | Detects ADB mDNS services | Installed by `pip install -e ".[dev]"` |
| `pygobject`, `pyudev` | Linux only | Legacy GTK host and Linux device integration | `pip install -e ".[dev,linux]"` |

## Recommended Windows Setup

Run these commands from a normal PowerShell session.

```powershell
winget install --id=astral-sh.uv -e
winget install --id=Google.PlatformTools -e
winget install --id=Genymobile.scrcpy -e
```

If `node` is not already installed, install Node.js LTS before building the frontend.

From the repository root:

```powershell
uv python install 3.12
uv venv
.venv\Scripts\Activate.ps1
uv pip install -e ".[dev]"
cd aurynk\web
npm install
npm run build
cd ..
python -m aurynk
```

If you are already inside `X:\code\fiscrpy\aurynk`, use:

```powershell
..\.venv\Scripts\Activate.ps1
python -m aurynk
```

## What Each Dependency Unlocks

- `adb`: required for pairing, connecting, disconnecting, screenshots, and device metadata.
- `scrcpy`: required only for the `Mirror` button.
- `qrcode` + `pillow`: required for QR code generation.
- `zeroconf`: required for QR pairing discovery and wireless service detection.
- `pywebview`: required for the desktop window. If it is missing, Aurynk may fall back to a browser-hosted UI instead of the native desktop shell.
- Node.js + npm: required only when building the frontend from source. A clean checkout does not include a tracked `web/dist` build output.

## Verification Commands

Use these before debugging the app itself.

```powershell
where.exe python
where.exe adb
where.exe scrcpy
node --version
npm --version
python -c "import PIL, webview, qrcode, zeroconf; print('python-deps-ok')"
```

Expected outcomes:

- `where.exe adb` prints the installed platform-tools path.
- `where.exe scrcpy` prints the installed scrcpy path.
- The Python import check prints `python-deps-ok`.

## Common Errors

### `No module named PIL`

Cause: `pillow` is missing.

Fix:

```powershell
.venv\Scripts\Activate.ps1
uv pip install pillow
```

### `WinError 2` or `The system cannot find the file specified`

Most often this means `adb` or `scrcpy` is missing.

Check:

```powershell
where.exe adb
where.exe scrcpy
```

Fix missing tools with:

```powershell
winget install --id=Google.PlatformTools -e
winget install --id=Genymobile.scrcpy -e
```

### QR pairing UI appears, but generating the QR code fails

Cause: `qrcode` or `pillow` is missing.

Fix:

```powershell
.venv\Scripts\Activate.ps1
uv pip install qrcode pillow
```

### Screenshot works, but `Mirror` does nothing

Cause: `scrcpy` is missing, not on `PATH`, or not configured in settings.

Check:

```powershell
where.exe scrcpy
scrcpy --version
```

If `scrcpy` is installed but Aurynk still cannot find it, set `scrcpy.scrcpy_path` in the settings file.

### The app starts but no desktop window appears

Cause: `pywebview` is missing or the local WebView backend is not available.

Fix:

```powershell
.venv\Scripts\Activate.ps1
uv pip install pywebview
```

If you still have renderer issues, install the Qt backend variant:

```powershell
uv pip install pywebview[qt]
```

## Config File and Manual Paths

Aurynk stores settings on Windows here:

```text
C:\Users\<username>\AppData\Roaming\Aurynk\settings.json
```

The two most important path overrides are:

```json
{
  "adb": {
    "adb_path": "C:\\Android\\platform-tools\\adb.exe"
  },
  "scrcpy": {
    "scrcpy_path": "C:\\Program Files\\scrcpy\\scrcpy.exe"
  }
}
```

Only set these when `adb` or `scrcpy` is installed but not discoverable through `PATH`.

## Linux Notes

Linux still works, but the dependency story is different:

- Runtime from source: `pip install -e ".[dev]"`
- Legacy GTK and `pyudev` support: `pip install -e ".[dev,linux]"`
- `adb` and `scrcpy` must still be installed from the system package manager

This file intentionally keeps the Windows path first because it is the least obvious setup and the one that produced the most real-world installation friction.
