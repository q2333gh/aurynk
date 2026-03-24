import json
import socket
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from aurynk.services.app_service import AppService
from aurynk.utils.logger import get_logger

logger = get_logger("HttpApi")


FALLBACK_HTML = """<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Aurynk</title>
  <style>
    :root { color-scheme: dark; font-family: "Segoe UI", Arial, sans-serif; }
    body { margin: 0; background: linear-gradient(180deg, #0f1519, #131d23); color: #eef4f6; }
    .shell { max-width: 1080px; margin: 0 auto; padding: 24px; }
    .hero, .panel { background: rgba(18, 25, 31, 0.9); border: 1px solid rgba(164, 190, 198, 0.12); border-radius: 18px; padding: 20px; box-shadow: 0 20px 50px rgba(0,0,0,.22); }
    .hero { display: flex; justify-content: space-between; gap: 16px; align-items: start; margin-bottom: 18px; }
    .hero h1 { margin: 0; font-size: 30px; line-height: 1.1; }
    .hero p { color: #9fb2bb; margin: 10px 0 0; }
    .layout { display: grid; grid-template-columns: 1.6fr 1fr; gap: 18px; }
    .stack { display: grid; gap: 18px; }
    .row { display: grid; gap: 8px; margin-bottom: 12px; }
    .pair-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    input, button { border-radius: 12px; border: 1px solid rgba(164, 190, 198, 0.16); padding: 11px 13px; font: inherit; }
    input { background: #0d1317; color: #eef4f6; }
    button { cursor: pointer; background: rgba(255,255,255,0.07); color: #eef4f6; }
    button.primary { background: linear-gradient(135deg, #d28d3d, #f0b25c); color: #11181d; font-weight: 700; border: none; }
    .device { padding: 14px; border-radius: 14px; border: 1px solid rgba(164, 190, 198, 0.08); background: rgba(255,255,255,0.04); margin-top: 12px; }
    .device h3, .panel h2 { margin: 0; }
    .meta { color: #9fb2bb; margin-top: 6px; font-size: 14px; }
    .actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 14px; }
    .banner { margin-bottom: 14px; padding: 12px 14px; border-radius: 12px; }
    .error { background: rgba(170, 58, 64, 0.2); border: 1px solid rgba(212, 90, 96, 0.3); }
    .ok { background: rgba(42, 137, 105, 0.18); border: 1px solid rgba(77, 183, 144, 0.32); }
    .muted { color: #9fb2bb; font-size: 14px; }
    @media (max-width: 900px) { .layout, .pair-grid, .hero { grid-template-columns: 1fr; display: grid; } }
  </style>
</head>
<body>
  <div class="shell">
    <div class="hero">
      <div>
        <h1>Aurynk Desktop Shell</h1>
        <p>Fallback desktop UI. The local API is active even when the bundled React build is unavailable.</p>
      </div>
      <button onclick="loadDevices()">Refresh</button>
    </div>
    <div id="message"></div>
    <div class="layout">
      <div class="stack">
        <section class="panel">
          <h2>Manual Pairing</h2>
          <p class="muted">Enter the wireless debugging coordinates and pairing code shown on your Android device.</p>
          <form id="pair-form" class="pair-grid">
            <div class="row"><label>Address</label><input name="address" placeholder="192.168.1.10" required /></div>
            <div class="row"><label>Pair Port</label><input name="pair_port" placeholder="38123" required /></div>
            <div class="row"><label>Connect Port</label><input name="connect_port" placeholder="34891" required /></div>
            <div class="row"><label>Password</label><input name="password" placeholder="123456" required /></div>
            <button class="primary" type="submit">Pair and Connect</button>
          </form>
        </section>
        <section class="panel">
          <h2>Devices</h2>
          <div id="devices" class="muted">Loading devices...</div>
        </section>
      </div>
      <aside class="panel">
        <h2>Fallback Mode</h2>
        <p class="muted">For the full desktop experience, build the React frontend in <code>web/</code>:</p>
        <pre><code>npm install
npm run build</code></pre>
        <p class="muted">This minimal UI still supports refresh, pairing, connect/disconnect, mirroring, and screenshots.</p>
      </aside>
    </div>
  </div>
  <script>
    const message = document.getElementById("message");
    const devicesRoot = document.getElementById("devices");

    function setMessage(text, kind = "ok") {
      if (!text) {
        message.innerHTML = "";
        return;
      }
      message.innerHTML = `<div class="banner ${kind}">${text}</div>`;
    }

    async function request(path, options = {}) {
      const response = await fetch(path, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || `Request failed: ${response.status}`);
      return payload;
    }

    async function loadDevices() {
      try {
        const payload = await request("/api/devices");
        renderDevices(payload.devices || []);
        setMessage("");
      } catch (error) {
        setMessage(error.message, "error");
      }
    }

    function renderDevices(devices) {
      if (!devices.length) {
        devicesRoot.innerHTML = '<p class="muted">No devices detected.</p>';
        return;
      }

      devicesRoot.innerHTML = devices.map((device) => `
        <article class="device">
          <h3>${device.name || device.address || device.adb_serial}</h3>
          <div class="meta">${device.address || device.adb_serial || ""} · ${device.connected ? "Connected" : (device.status || "Disconnected")}</div>
          <div class="actions">
            ${device.type === "wireless" ? `<button onclick="connectDevice('${device.address}')">Connect</button>` : ""}
            ${device.type === "wireless" ? `<button onclick="disconnectDevice('${device.address}')">Disconnect</button>` : ""}
            <button onclick='mirrorDevice(${JSON.stringify(device)})'>${device.mirroring ? "Stop Mirror" : "Mirror"}</button>
            <button onclick='screenshotDevice(${JSON.stringify(device)})'>Screenshot</button>
          </div>
        </article>
      `).join("");
    }

    async function connectDevice(address) {
      try {
        await request("/api/connect", { method: "POST", body: JSON.stringify({ address }) });
        await loadDevices();
      } catch (error) {
        setMessage(error.message, "error");
      }
    }

    async function disconnectDevice(address) {
      try {
        await request("/api/disconnect", { method: "POST", body: JSON.stringify({ address }) });
        await loadDevices();
      } catch (error) {
        setMessage(error.message, "error");
      }
    }

    async function mirrorDevice(device) {
      try {
        const endpoint = device.mirroring ? "/api/mirror/stop" : "/api/mirror/start";
        await request(endpoint, { method: "POST", body: JSON.stringify(device) });
        await loadDevices();
      } catch (error) {
        setMessage(error.message, "error");
      }
    }

    async function screenshotDevice(device) {
      try {
        const result = await request("/api/screenshot", { method: "POST", body: JSON.stringify(device) });
        setMessage(`Screenshot saved to ${result.path}`);
      } catch (error) {
        setMessage(error.message, "error");
      }
    }

    document.getElementById("pair-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      const payload = Object.fromEntries(form.entries());
      payload.pair_port = Number(payload.pair_port);
      payload.connect_port = Number(payload.connect_port);

      try {
        await request("/api/pair", { method: "POST", body: JSON.stringify(payload) });
        event.currentTarget.reset();
        setMessage("Device paired successfully.");
        await loadDevices();
      } catch (error) {
        setMessage(error.message, "error");
      }
    });

    loadDevices();
    setInterval(loadDevices, 3000);
  </script>
</body>
</html>
"""


class ApiServer:
    def __init__(
        self,
        service: AppService | None = None,
        static_dir: Path | None = None,
        fallback_factory: Callable[[], str] | None = None,
    ) -> None:
        self.service = service or AppService()
        self.static_dir = static_dir
        self.fallback_factory = fallback_factory or (lambda: FALLBACK_HTML)
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.base_url: str | None = None

    def start(self) -> str:
        if self._server:
            return self.base_url or ""

        host = "127.0.0.1"
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((host, 0))
            port = sock.getsockname()[1]

        handler = self._make_handler()
        self._server = ThreadingHTTPServer((host, port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self.base_url = f"http://{host}:{port}"
        return self.base_url

    def stop(self) -> None:
        if not self._server:
            return
        self._server.shutdown()
        self._server.server_close()
        self._server = None
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def _make_handler(self):
        service = self.service
        static_dir = self.static_dir
        fallback_factory = self.fallback_factory

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlparse(self.path)
                if parsed.path == "/api/devices":
                    self._write_json({"devices": service.get_devices()})
                    return
                if parsed.path == "/api/settings":
                    self._write_json({"settings": service.get_settings()})
                    return
                if parsed.path == "/api/pair/qr":
                    self._write_json(service.get_qr_pairing_status())
                    return
                self._serve_static(parsed.path)

            def do_POST(self):
                parsed = urlparse(self.path)
                payload = self._read_json()

                try:
                    if parsed.path == "/api/pair":
                        response = service.pair_device(payload)
                    elif parsed.path == "/api/pair/qr/start":
                        response = service.start_qr_pairing()
                    elif parsed.path == "/api/pair/qr/cancel":
                        response = service.cancel_qr_pairing()
                    elif parsed.path == "/api/connect":
                        response = service.connect_device(str(payload.get("address", "")))
                    elif parsed.path == "/api/disconnect":
                        response = service.disconnect_device(str(payload.get("address", "")))
                    elif parsed.path == "/api/mirror/start":
                        response = service.start_mirror(payload)
                    elif parsed.path == "/api/mirror/stop":
                        response = service.stop_mirror(payload)
                    elif parsed.path == "/api/screenshot":
                        response = service.take_screenshot(payload)
                    elif parsed.path == "/api/settings":
                        response = {"settings": service.update_settings(payload)}
                    elif parsed.path == "/api/open":
                        response = service.open_target(payload)
                    else:
                        self._write_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
                        return
                except ValueError as exc:
                    self._write_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                    return
                except RuntimeError as exc:
                    self._write_json({"error": str(exc)}, HTTPStatus.CONFLICT)
                    return
                except Exception as exc:
                    logger.exception("Unhandled API error")
                    self._write_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
                    return

                self._write_json(response)

            def log_message(self, format, *args):
                logger.debug("%s - %s", self.address_string(), format % args)

            def _read_json(self):
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0:
                    return {}
                raw = self.rfile.read(length)
                if not raw:
                    return {}
                return json.loads(raw.decode("utf-8"))

            def _write_json(self, payload, status=HTTPStatus.OK):
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def _serve_static(self, path: str):
                if path.startswith("/api/"):
                    self._write_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
                    return

                candidate = "index.html" if path in ("", "/") else path.lstrip("/")
                if static_dir:
                    file_path = static_dir / candidate
                    if file_path.is_file():
                        self._write_file(file_path)
                        return
                    if not Path(candidate).suffix:
                        index_path = static_dir / "index.html"
                        if index_path.is_file():
                            self._write_file(index_path)
                            return

                body = fallback_factory().encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _write_file(self, file_path: Path):
                content = file_path.read_bytes()
                content_type = {
                    ".html": "text/html; charset=utf-8",
                    ".js": "application/javascript; charset=utf-8",
                    ".css": "text/css; charset=utf-8",
                    ".svg": "image/svg+xml",
                    ".png": "image/png",
                    ".webp": "image/webp",
                    ".json": "application/json; charset=utf-8",
                }.get(file_path.suffix.lower(), "application/octet-stream")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)

        return Handler
