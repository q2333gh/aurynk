import base64
import io
import threading
from dataclasses import dataclass, field
from typing import Any

from aurynk.core.adb_manager import ADBController
from aurynk.utils.adb_utils import resolve_adb_path
from aurynk.utils.logger import get_logger
from aurynk.utils.settings import SettingsManager

logger = get_logger("QrPairingService")


@dataclass
class PairingSession:
    network_name: str
    password: str
    qr_data: str
    qr_image_data_url: str
    status: str = "waiting_for_scan"
    message: str = "Scan the QR code with your phone"
    address: str | None = None
    pair_port: int | None = None
    connect_port: int | None = None
    error: str | None = None
    session_id: str | None = None
    cancelled: bool = False
    zeroconf: Any = None
    timeout: int = 60
    lock: threading.Lock = field(default_factory=threading.Lock)


class QrPairingService:
    def __init__(
        self,
        adb_controller: ADBController | None = None,
        settings: SettingsManager | None = None,
    ) -> None:
        self.adb_controller = adb_controller or ADBController()
        self.settings = settings or SettingsManager()
        self._session: PairingSession | None = None
        self._session_lock = threading.Lock()

    def start_session(self) -> dict[str, Any]:
        resolve_adb_path(raise_on_missing=True)

        network_name = f"ADB_WIFI_{self.adb_controller.generate_code(5)}"
        password = self.adb_controller.generate_code(5)
        qr_data = f"WIFI:T:ADB;S:{network_name};P:{password};;"
        image_url = self._build_qr_data_url(qr_data)
        timeout = int(self.settings.get("adb", "qr_timeout", 60) or 60)
        session = PairingSession(
            network_name=network_name,
            password=password,
            qr_data=qr_data,
            qr_image_data_url=image_url,
            timeout=timeout,
            session_id=self.adb_controller.generate_code(10),
        )

        with self._session_lock:
            self._close_session(self._session)
            self._session = session

        threading.Thread(target=self._discover_devices, args=(session,), daemon=True).start()
        threading.Thread(target=self._expire_session, args=(session,), daemon=True).start()

        return self.get_status()

    def cancel_session(self) -> dict[str, Any]:
        with self._session_lock:
            if self._session:
                self._session.cancelled = True
                self._session.status = "cancelled"
                self._session.message = "QR pairing cancelled"
                self._close_session(self._session)
        return self.get_status()

    def get_status(self) -> dict[str, Any]:
        with self._session_lock:
            session = self._session
            if not session:
                return {"active": False}
            with session.lock:
                return {
                    "active": True,
                    "session_id": session.session_id,
                    "status": session.status,
                    "message": session.message,
                    "error": session.error,
                    "qr_image_data_url": session.qr_image_data_url,
                    "network_name": session.network_name,
                    "password": session.password,
                    "address": session.address,
                    "pair_port": session.pair_port,
                    "connect_port": session.connect_port,
                    "timeout": session.timeout,
                }

    def _discover_devices(self, session: PairingSession) -> None:
        def on_device_found(address, pair_port, connect_port, _password):
            self._on_device_found(session, address, pair_port, connect_port)

        try:
            zeroconf, _browser = self.adb_controller.start_mdns_discovery(
                on_device_found,
                session.network_name,
                session.password,
            )
            with session.lock:
                if session.cancelled:
                    try:
                        zeroconf.close()
                    except Exception:
                        pass
                    return
                session.zeroconf = zeroconf
                session.message = "Waiting for your Android device to advertise pairing service"
        except Exception as exc:
            logger.exception("QR discovery failed")
            with session.lock:
                session.status = "error"
                session.error = str(exc)
                session.message = str(exc)

    def _on_device_found(
        self, session: PairingSession, address: str, pair_port: int, connect_port: int
    ) -> None:
        with session.lock:
            if session.cancelled or session.status in {"pairing", "paired"}:
                return
            session.status = "pairing"
            session.message = f"Device found: {address}. Pairing..."
            session.address = address
            session.pair_port = pair_port
            session.connect_port = connect_port

        def pair():
            try:
                success = self.adb_controller.pair_device(
                    address,
                    pair_port,
                    connect_port,
                    session.password,
                    status_callback=lambda msg: self._update_message(session, msg),
                )
                with session.lock:
                    if session.cancelled:
                        return
                    if success:
                        session.status = "paired"
                        session.message = "Device paired successfully"
                    else:
                        session.status = "error"
                        session.error = "Pairing failed"
                        session.message = "Pairing failed"
            except Exception as exc:
                logger.exception("QR pairing failed")
                with session.lock:
                    session.status = "error"
                    session.error = str(exc)
                    session.message = str(exc)
            finally:
                self._close_session(session)

        threading.Thread(target=pair, daemon=True).start()

    def _expire_session(self, session: PairingSession) -> None:
        import time

        time.sleep(session.timeout)
        with session.lock:
            if session.cancelled or session.status in {"paired", "error"}:
                return
            session.status = "expired"
            session.message = "QR code expired. Try again."
        self._close_session(session)

    def _update_message(self, session: PairingSession, message: str) -> None:
        with session.lock:
            if not session.cancelled:
                session.message = message

    def _close_session(self, session: PairingSession | None) -> None:
        if not session or not session.zeroconf:
            return
        try:
            session.zeroconf.close()
        except Exception:
            logger.debug("Failed to close zeroconf session", exc_info=True)
        finally:
            session.zeroconf = None

    def _build_qr_data_url(self, qr_data: str) -> str:
        try:
            import qrcode
        except ImportError as exc:
            raise RuntimeError("qrcode is not installed") from exc

        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(qr_data)
        qr_image = qr.make_image()
        buffer = io.BytesIO()
        qr_image.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
