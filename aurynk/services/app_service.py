import subprocess
from copy import deepcopy
from typing import Any

from aurynk.core.adb_manager import ADBController
from aurynk.core.scrcpy_runner import ScrcpyManager
from aurynk.platform.system_integration import SystemIntegration
from aurynk.services.qr_pairing_service import QrPairingService
from aurynk.utils.adb_utils import get_adb_path, resolve_adb_path
from aurynk.utils.logger import get_logger
from aurynk.utils.settings import SettingsManager

logger = get_logger("AppService")


class AppService:
    def __init__(
        self,
        adb_controller: ADBController | None = None,
        settings: SettingsManager | None = None,
        system: SystemIntegration | None = None,
        scrcpy_manager: ScrcpyManager | None = None,
    ) -> None:
        self.adb_controller = adb_controller or ADBController()
        self.settings = settings or SettingsManager()
        self.system = system or SystemIntegration()
        self.scrcpy = scrcpy_manager or ScrcpyManager()
        self.qr_pairing = QrPairingService(self.adb_controller, self.settings)

    def get_devices(self) -> list[dict[str, Any]]:
        paired_devices = self.adb_controller.load_paired_devices()
        adb_devices = self._get_adb_device_state()
        devices: list[dict[str, Any]] = []

        for device in paired_devices:
            current = deepcopy(device)
            serial = self._wireless_serial(device)
            current["id"] = device.get("address") or serial
            current["type"] = "wireless"
            current["connected"] = serial in adb_devices and adb_devices[serial] == "device"
            current["adb_serial"] = serial
            current["status"] = adb_devices.get(serial, "disconnected")
            current["mirroring"] = bool(
                serial and device.get("connect_port") and self.scrcpy.is_mirroring(
                    device["address"], device["connect_port"]
                )
            )
            devices.append(current)

        paired_serials = {self._wireless_serial(device) for device in paired_devices}
        for serial, status in adb_devices.items():
            if serial in paired_serials or ":" in serial:
                continue
            devices.append(
                {
                    "id": serial,
                    "type": "usb",
                    "name": serial,
                    "adb_serial": serial,
                    "connected": status == "device",
                    "status": status,
                    "mirroring": self.scrcpy.is_mirroring_serial(serial),
                }
            )

        return devices

    def pair_device(self, payload: dict[str, Any]) -> dict[str, Any]:
        required = ["address", "pair_port", "connect_port", "password"]
        missing = [key for key in required if key not in payload or payload[key] in (None, "")]
        if missing:
            raise ValueError(f"Missing fields: {', '.join(missing)}")
        self._require_adb()

        success = self.adb_controller.pair_device(
            str(payload["address"]).strip(),
            int(payload["pair_port"]),
            int(payload["connect_port"]),
            str(payload["password"]).strip(),
        )
        if not success:
            raise RuntimeError("Pairing failed")

        device = next(
            (
                entry
                for entry in self.adb_controller.load_paired_devices()
                if entry.get("address") == str(payload["address"]).strip()
            ),
            None,
        )
        return {"success": True, "device": device}

    def connect_device(self, address: str) -> dict[str, Any]:
        adb_path = self._require_adb()
        device = self._get_stored_device(address)
        connect_port = device.get("connect_port")
        if not connect_port:
            raise ValueError("Device is missing connect_port")

        result = subprocess.run(
            [adb_path, "connect", f"{address}:{connect_port}"],
            capture_output=True,
            text=True,
            timeout=self.settings.get("adb", "connection_timeout", 10),
        )
        output = f"{result.stdout}\n{result.stderr}".strip()
        connected = result.returncode == 0 and "unable" not in output.lower()
        if connected:
            self.system.notify("Device connected", device.get("name", address))
        return {"success": connected, "output": output}

    def disconnect_device(self, address: str) -> dict[str, Any]:
        adb_path = self._require_adb()
        device = self._get_stored_device(address)
        connect_port = device.get("connect_port")
        if not connect_port:
            raise ValueError("Device is missing connect_port")

        result = subprocess.run(
            [adb_path, "disconnect", f"{address}:{connect_port}"],
            capture_output=True,
            text=True,
            timeout=self.settings.get("adb", "connection_timeout", 10),
        )
        output = f"{result.stdout}\n{result.stderr}".strip()
        return {"success": result.returncode == 0, "output": output}

    def start_mirror(self, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("type") == "usb":
            serial = payload.get("adb_serial")
            if not serial:
                raise ValueError("Missing adb_serial for USB mirror")
            success = self.scrcpy.start_mirror_usb(str(serial), payload.get("name"))
        else:
            address = payload.get("address")
            connect_port = payload.get("connect_port")
            if not address or not connect_port:
                raise ValueError("Missing wireless device coordinates")
            success = self.scrcpy.start_mirror(str(address), int(connect_port), payload.get("name"))

        if not success:
            raise RuntimeError("Failed to start mirroring")
        return {"success": True}

    def stop_mirror(self, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("type") == "usb":
            serial = payload.get("adb_serial")
            if not serial:
                raise ValueError("Missing adb_serial for USB mirror")
            success = self.scrcpy.stop_mirror_by_serial(str(serial))
        else:
            address = payload.get("address")
            connect_port = payload.get("connect_port")
            if not address or not connect_port:
                raise ValueError("Missing wireless device coordinates")
            success = self.scrcpy.stop_mirror(str(address), int(connect_port))
        return {"success": success}

    def take_screenshot(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_adb()
        if payload.get("type") == "usb":
            serial = payload.get("adb_serial")
            if not serial:
                raise ValueError("Missing adb_serial for USB screenshot")
            path = self.adb_controller.capture_screenshot_by_serial(str(serial))
        else:
            address = payload.get("address")
            connect_port = payload.get("connect_port")
            if not address or not connect_port:
                raise ValueError("Missing wireless device coordinates")
            path = self.adb_controller.capture_screenshot(str(address), int(connect_port))

        if not path:
            raise RuntimeError("Failed to capture screenshot")
        return {"success": True, "path": path}

    def get_settings(self) -> dict[str, Any]:
        return self.settings.get_all()

    def update_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        for category, values in payload.items():
            if not isinstance(values, dict):
                continue
            for key, value in values.items():
                self.settings.set(category, key, value, save_immediately=False)
        self.settings.save()
        return self.settings.get_all()

    def open_target(self, payload: dict[str, Any]) -> dict[str, Any]:
        target = payload.get("target")
        kind = payload.get("kind", "path")
        if not target:
            raise ValueError("Missing target")

        if kind == "url":
            ok = self.system.open_url(str(target))
        else:
            ok = self.system.open_path(str(target))
        return {"success": ok}

    def start_qr_pairing(self) -> dict[str, Any]:
        try:
            return self.qr_pairing.start_session()
        except FileNotFoundError as exc:
            raise RuntimeError(str(exc)) from exc

    def get_qr_pairing_status(self) -> dict[str, Any]:
        return self.qr_pairing.get_status()

    def cancel_qr_pairing(self) -> dict[str, Any]:
        return self.qr_pairing.cancel_session()

    def _get_stored_device(self, address: str) -> dict[str, Any]:
        for device in self.adb_controller.load_paired_devices():
            if device.get("address") == address:
                return device
        raise ValueError(f"Unknown device: {address}")

    def _wireless_serial(self, device: dict[str, Any]) -> str | None:
        address = device.get("address")
        connect_port = device.get("connect_port")
        if not address or not connect_port:
            return None
        return f"{address}:{connect_port}"

    def _get_adb_device_state(self) -> dict[str, str]:
        try:
            adb_path = resolve_adb_path(raise_on_missing=True)
            result = subprocess.run(
                [adb_path, "devices"],
                capture_output=True,
                text=True,
                timeout=self.settings.get("adb", "connection_timeout", 10),
            )
        except FileNotFoundError:
            return {}

        if result.returncode != 0:
            logger.warning("adb devices failed: %s", result.stderr.strip())
            return {}

        states: dict[str, str] = {}
        for line in result.stdout.splitlines()[1:]:
            line = line.strip()
            if not line or "\t" not in line:
                continue
            serial, state = line.split("\t", 1)
            states[serial.strip()] = state.strip()
        return states

    def _require_adb(self) -> str:
        try:
            return resolve_adb_path(raise_on_missing=True)
        except FileNotFoundError as exc:
            raise RuntimeError(str(exc)) from exc
