import unittest
from unittest.mock import MagicMock, patch

from aurynk.services.app_service import AppService


class TestAppService(unittest.TestCase):
    def setUp(self):
        self.adb_controller = MagicMock()
        self.settings = MagicMock()
        self.settings.get.side_effect = lambda category, key, default=None: default
        self.system = MagicMock()
        self.scrcpy = MagicMock()
        self.service = AppService(
            adb_controller=self.adb_controller,
            settings=self.settings,
            system=self.system,
            scrcpy_manager=self.scrcpy,
        )

    @patch("aurynk.services.app_service.resolve_adb_path", return_value="adb")
    @patch("aurynk.services.app_service.subprocess.run")
    def test_get_devices_merges_wireless_and_usb_state(self, mock_run, _mock_resolve_adb_path):
        self.adb_controller.load_paired_devices.return_value = [
            {"address": "192.168.1.8", "connect_port": 5555, "name": "Pixel"}
        ]
        self.scrcpy.is_mirroring.return_value = True
        self.scrcpy.is_mirroring_serial.return_value = False
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="List of devices attached\n192.168.1.8:5555\tdevice\nUSB123\tdevice\n",
            stderr="",
        )

        devices = self.service.get_devices()

        self.assertEqual(len(devices), 2)
        wireless = next(device for device in devices if device["type"] == "wireless")
        usb = next(device for device in devices if device["type"] == "usb")
        self.assertTrue(wireless["connected"])
        self.assertTrue(wireless["mirroring"])
        self.assertEqual(usb["adb_serial"], "USB123")

    @patch("aurynk.services.app_service.resolve_adb_path", return_value="adb")
    @patch("aurynk.services.app_service.subprocess.run")
    def test_connect_device(self, mock_run, _mock_resolve_adb_path):
        self.adb_controller.load_paired_devices.return_value = [
            {"address": "192.168.1.8", "connect_port": 5555, "name": "Pixel"}
        ]
        mock_run.return_value = MagicMock(returncode=0, stdout="connected", stderr="")

        result = self.service.connect_device("192.168.1.8")

        self.assertTrue(result["success"])
        self.system.notify.assert_called_once()

    def test_update_settings(self):
        payload = {"app": {"theme": "dark"}, "scrcpy": {"video_bitrate": 12}}
        self.settings.get_all.return_value = payload

        result = self.service.update_settings(payload)

        self.settings.set.assert_any_call("app", "theme", "dark", save_immediately=False)
        self.settings.set.assert_any_call(
            "scrcpy", "video_bitrate", 12, save_immediately=False
        )
        self.settings.save.assert_called_once()
        self.assertEqual(result, payload)

    @patch("aurynk.services.app_service.resolve_adb_path", return_value="adb")
    def test_take_usb_screenshot(self, _mock_resolve_adb_path):
        self.adb_controller.capture_screenshot_by_serial.return_value = "C:/tmp/screen.png"

        result = self.service.take_screenshot({"type": "usb", "adb_serial": "USB123"})

        self.assertEqual(result["path"], "C:/tmp/screen.png")

    def test_get_qr_pairing_status(self):
        self.service.qr_pairing = MagicMock()
        self.service.qr_pairing.get_status.return_value = {"active": True, "status": "waiting_for_scan"}

        result = self.service.get_qr_pairing_status()

        self.assertTrue(result["active"])


if __name__ == "__main__":
    unittest.main()
