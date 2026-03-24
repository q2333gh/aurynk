import json
import tempfile
import unittest
import urllib.request
from pathlib import Path

from aurynk.api.http_api import ApiServer


class FakeService:
    def get_devices(self):
        return [{"id": "device-1", "type": "wireless", "name": "Pixel"}]

    def get_settings(self):
        return {"app": {"theme": "system"}}

    def get_qr_pairing_status(self):
        return {"active": True, "status": "waiting_for_scan"}

    def start_qr_pairing(self):
        return {
            "active": True,
            "status": "waiting_for_scan",
            "qr_image_data_url": "data:image/png;base64,abc",
        }

    def cancel_qr_pairing(self):
        return {"active": False, "status": "cancelled"}

    def update_settings(self, payload):
        return payload

    def pair_device(self, payload):
        return {"success": True, "device": payload}

    def connect_device(self, address):
        return {"success": True, "address": address}

    def disconnect_device(self, address):
        return {"success": True, "address": address}

    def start_mirror(self, payload):
        return {"success": True, "payload": payload}

    def stop_mirror(self, payload):
        return {"success": True, "payload": payload}

    def take_screenshot(self, payload):
        return {"success": True, "path": "/tmp/screen.png"}

    def open_target(self, payload):
        return {"success": True, "payload": payload}


class TestHttpApi(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        static_dir = Path(self.tempdir.name)
        (static_dir / "index.html").write_text("<html><body>Aurynk</body></html>", encoding="utf-8")
        self.server = ApiServer(service=FakeService(), static_dir=static_dir)
        self.base_url = self.server.start()

    def tearDown(self):
        self.server.stop()
        self.tempdir.cleanup()

    def test_get_devices(self):
        with urllib.request.urlopen(f"{self.base_url}/api/devices") as response:
            payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(payload["devices"][0]["id"], "device-1")

    def test_post_settings(self):
        request = urllib.request.Request(
            f"{self.base_url}/api/settings",
            data=json.dumps({"app": {"theme": "dark"}}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(payload["settings"]["app"]["theme"], "dark")

    def test_serves_static_index(self):
        with urllib.request.urlopen(f"{self.base_url}/") as response:
            content = response.read().decode("utf-8")

        self.assertIn("Aurynk", content)

    def test_get_qr_pairing_status(self):
        with urllib.request.urlopen(f"{self.base_url}/api/pair/qr") as response:
            payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(payload["status"], "waiting_for_scan")


if __name__ == "__main__":
    unittest.main()
