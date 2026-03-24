import { Monitor, RefreshCw, Settings, Smartphone, Usb, Camera, Link2, Link2Off } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

const defaultSettings = {
  app: {
    show_notifications: true,
    close_to_tray: false,
    theme: "system",
  },
  adb: {
    connection_timeout: 10,
    max_retry_attempts: 5,
  },
  scrcpy: {
    always_on_top: false,
    enable_audio: false,
    video_bitrate: 8,
    max_fps: 0,
  },
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : null;

  if (!response.ok) {
    throw new Error(payload?.error || `Request failed: ${response.status}`);
  }

  return payload;
}

function App() {
  const [devices, setDevices] = useState([]);
  const [settings, setSettings] = useState(defaultSettings);
  const [pairForm, setPairForm] = useState({
    address: "",
    pair_port: "",
    connect_port: "",
    password: "",
  });
  const [qrPairing, setQrPairing] = useState({ active: false });
  const [busyKey, setBusyKey] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [showSettings, setShowSettings] = useState(true);

  const groupedDevices = useMemo(() => {
    return {
      wireless: devices.filter((device) => device.type === "wireless"),
      usb: devices.filter((device) => device.type === "usb"),
    };
  }, [devices]);

  async function loadDevices() {
    try {
      const payload = await api("/api/devices");
      setDevices(payload.devices || []);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadSettings() {
    try {
      const payload = await api("/api/settings");
      setSettings((current) => ({ ...current, ...(payload.settings || {}) }));
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    loadDevices();
    loadSettings();
    const timer = window.setInterval(loadDevices, 3000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    loadQrPairingStatus();
    const timer = window.setInterval(loadQrPairingStatus, 2000);
    return () => window.clearInterval(timer);
  }, []);

  async function handlePair(event) {
    event.preventDefault();
    setBusyKey("pair");
    setNotice("");
    setError("");
    try {
      await api("/api/pair", {
        method: "POST",
        body: JSON.stringify({
          ...pairForm,
          pair_port: Number(pairForm.pair_port),
          connect_port: Number(pairForm.connect_port),
        }),
      });
      setNotice("Device paired successfully.");
      setPairForm({
        address: "",
        pair_port: "",
        connect_port: "",
        password: "",
      });
      await loadDevices();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyKey("");
    }
  }

  async function loadQrPairingStatus() {
    try {
      const payload = await api("/api/pair/qr");
      setQrPairing(payload);
    } catch (err) {
      setError(err.message);
    }
  }

  async function startQrPairing() {
    setBusyKey("qr-start");
    setNotice("");
    setError("");
    try {
      const payload = await api("/api/pair/qr/start", { method: "POST", body: "{}" });
      setQrPairing(payload);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyKey("");
    }
  }

  async function cancelQrPairing() {
    setBusyKey("qr-cancel");
    try {
      const payload = await api("/api/pair/qr/cancel", { method: "POST", body: "{}" });
      setQrPairing(payload);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyKey("");
    }
  }

  async function runDeviceAction(action, device, payload = {}) {
    const key = `${action}:${device.id}`;
    setBusyKey(key);
    setNotice("");
    setError("");
    try {
      const result = await api(`/api/${action}`, {
        method: "POST",
        body: JSON.stringify({
          ...device,
          ...payload,
        }),
      });
      if (action === "screenshot" && result.path) {
        const folder = result.path.replace(/[\\/][^\\/]+$/, "");
        await api("/api/open", {
          method: "POST",
          body: JSON.stringify({ target: folder, kind: "path" }),
        });
      }
      await loadDevices();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyKey("");
    }
  }

  async function saveSettings() {
    setBusyKey("save-settings");
    setNotice("");
    setError("");
    try {
      const payload = await api("/api/settings", {
        method: "POST",
        body: JSON.stringify(settings),
      });
      setSettings(payload.settings || settings);
      setNotice("Settings saved.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyKey("");
    }
  }

  function updateSetting(section, key, value) {
    setSettings((current) => ({
      ...current,
      [section]: {
        ...current[section],
        [key]: value,
      },
    }));
  }

  return (
    <div className="app-shell">
      <div className="ambient ambient-a" />
      <div className="ambient ambient-b" />

      <header className="topbar">
        <div>
          <p className="eyebrow">Aurynk Desktop</p>
          <h1>Android device control for Linux and Windows</h1>
        </div>
        <div className="topbar-actions">
          <button className="ghost-button" onClick={loadDevices}>
            <RefreshCw size={16} />
            Refresh
          </button>
          <button className="ghost-button" onClick={() => setShowSettings((value) => !value)}>
            <Settings size={16} />
            {showSettings ? "Hide Settings" : "Show Settings"}
          </button>
        </div>
      </header>

      {error ? <div className="banner banner-error">{error}</div> : null}
      {notice ? <div className="banner banner-ok">{notice}</div> : null}

      <main className="layout">
        <section className="primary-column">
          <div className="panel">
            <div className="panel-header">
              <div>
                <p className="panel-kicker">Pair Device</p>
                <h2>Manual wireless pairing</h2>
              </div>
            </div>
            <div className="qr-pairing">
              <div className="qr-copy">
                <p className="panel-kicker">QR Pairing</p>
                <h3>Scan on Android Wireless Debugging</h3>
                <p className="qr-description">
                  On your phone, open Developer Options, enter Wireless Debugging, then tap
                  "Pair device with QR code".
                </p>
                <div className="qr-actions">
                  <button
                    className="primary-button"
                    type="button"
                    disabled={busyKey === "qr-start"}
                    onClick={startQrPairing}
                  >
                    {busyKey === "qr-start" ? "Generating..." : "Generate QR"}
                  </button>
                  {qrPairing.active ? (
                    <button
                      className="ghost-button"
                      type="button"
                      disabled={busyKey === "qr-cancel"}
                      onClick={cancelQrPairing}
                    >
                      Cancel
                    </button>
                  ) : null}
                </div>
                <p className="qr-status">
                  {qrPairing.message || "Generate a fresh QR code to start pairing."}
                </p>
              </div>
              <div className="qr-card">
                {qrPairing.active && qrPairing.qr_image_data_url ? (
                  <img className="qr-image" src={qrPairing.qr_image_data_url} alt="Aurynk QR pairing code" />
                ) : (
                  <div className="qr-placeholder">QR code will appear here</div>
                )}
              </div>
            </div>
            <form className="pair-grid" onSubmit={handlePair}>
              <label>
                <span>Address</span>
                <input
                  value={pairForm.address}
                  onChange={(event) => setPairForm((current) => ({ ...current, address: event.target.value }))}
                  placeholder="192.168.1.10"
                />
              </label>
              <label>
                <span>Pair Port</span>
                <input
                  value={pairForm.pair_port}
                  onChange={(event) => setPairForm((current) => ({ ...current, pair_port: event.target.value }))}
                  placeholder="38123"
                />
              </label>
              <label>
                <span>Connect Port</span>
                <input
                  value={pairForm.connect_port}
                  onChange={(event) => setPairForm((current) => ({ ...current, connect_port: event.target.value }))}
                  placeholder="34891"
                />
              </label>
              <label>
                <span>Password</span>
                <input
                  value={pairForm.password}
                  onChange={(event) => setPairForm((current) => ({ ...current, password: event.target.value }))}
                  placeholder="123456"
                />
              </label>
              <button className="primary-button" type="submit" disabled={busyKey === "pair"}>
                {busyKey === "pair" ? "Pairing..." : "Pair and Connect"}
              </button>
            </form>
          </div>

          <DeviceSection
            title="Wireless Devices"
            kicker="Paired"
            icon={<Smartphone size={18} />}
            devices={groupedDevices.wireless}
            busyKey={busyKey}
            onConnect={(device) => runDeviceAction("connect", device, { address: device.address })}
            onDisconnect={(device) => runDeviceAction("disconnect", device, { address: device.address })}
            onMirror={(device) =>
              runDeviceAction(device.mirroring ? "mirror/stop" : "mirror/start", device)
            }
            onScreenshot={(device) => runDeviceAction("screenshot", device)}
          />

          <DeviceSection
            title="USB Devices"
            kicker="ADB"
            icon={<Usb size={18} />}
            devices={groupedDevices.usb}
            busyKey={busyKey}
            onMirror={(device) =>
              runDeviceAction(device.mirroring ? "mirror/stop" : "mirror/start", device)
            }
            onScreenshot={(device) => runDeviceAction("screenshot", device)}
          />
        </section>

        {showSettings ? (
          <aside className="side-column">
            <div className="panel sticky-panel">
              <div className="panel-header">
                <div>
                  <p className="panel-kicker">Settings</p>
                  <h2>Cross-platform defaults</h2>
                </div>
              </div>

              <div className="settings-group">
                <h3>Application</h3>
                <label className="toggle-row">
                  <span>Show notifications</span>
                  <input
                    type="checkbox"
                    checked={Boolean(settings.app?.show_notifications)}
                    onChange={(event) => updateSetting("app", "show_notifications", event.target.checked)}
                  />
                </label>
                <label className="field-row">
                  <span>Theme</span>
                  <select
                    value={settings.app?.theme || "system"}
                    onChange={(event) => updateSetting("app", "theme", event.target.value)}
                  >
                    <option value="system">System</option>
                    <option value="light">Light</option>
                    <option value="dark">Dark</option>
                  </select>
                </label>
              </div>

              <div className="settings-group">
                <h3>ADB</h3>
                <label className="field-row">
                  <span>ADB path</span>
                  <input
                    value={settings.adb?.adb_path ?? ""}
                    onChange={(event) => updateSetting("adb", "adb_path", event.target.value)}
                    placeholder="C:\\Android\\platform-tools\\adb.exe"
                  />
                </label>
                <label className="field-row">
                  <span>Connection timeout</span>
                  <input
                    type="number"
                    value={settings.adb?.connection_timeout ?? 10}
                    onChange={(event) =>
                      updateSetting("adb", "connection_timeout", Number(event.target.value))
                    }
                  />
                </label>
                <label className="field-row">
                  <span>Retry attempts</span>
                  <input
                    type="number"
                    value={settings.adb?.max_retry_attempts ?? 5}
                    onChange={(event) =>
                      updateSetting("adb", "max_retry_attempts", Number(event.target.value))
                    }
                  />
                </label>
              </div>

              <div className="settings-group">
                <h3>scrcpy</h3>
                <label className="toggle-row">
                  <span>Always on top</span>
                  <input
                    type="checkbox"
                    checked={Boolean(settings.scrcpy?.always_on_top)}
                    onChange={(event) =>
                      updateSetting("scrcpy", "always_on_top", event.target.checked)
                    }
                  />
                </label>
                <label className="toggle-row">
                  <span>Enable audio</span>
                  <input
                    type="checkbox"
                    checked={Boolean(settings.scrcpy?.enable_audio)}
                    onChange={(event) =>
                      updateSetting("scrcpy", "enable_audio", event.target.checked)
                    }
                  />
                </label>
                <label className="field-row">
                  <span>Video bitrate (Mbps)</span>
                  <input
                    type="number"
                    value={settings.scrcpy?.video_bitrate ?? 8}
                    onChange={(event) =>
                      updateSetting("scrcpy", "video_bitrate", Number(event.target.value))
                    }
                  />
                </label>
                <label className="field-row">
                  <span>Max FPS</span>
                  <input
                    type="number"
                    value={settings.scrcpy?.max_fps ?? 0}
                    onChange={(event) =>
                      updateSetting("scrcpy", "max_fps", Number(event.target.value))
                    }
                  />
                </label>
              </div>

              <button
                className="primary-button wide"
                disabled={busyKey === "save-settings"}
                onClick={saveSettings}
              >
                {busyKey === "save-settings" ? "Saving..." : "Save Settings"}
              </button>
            </div>
          </aside>
        ) : null}
      </main>
    </div>
  );
}

function DeviceSection({
  title,
  kicker,
  icon,
  devices,
  busyKey,
  onConnect,
  onDisconnect,
  onMirror,
  onScreenshot,
}) {
  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <p className="panel-kicker">{kicker}</p>
          <h2>{title}</h2>
        </div>
      </div>

      <div className="device-grid">
        {devices.length === 0 ? (
          <div className="empty-state">No devices detected.</div>
        ) : (
          devices.map((device) => {
            const stateText = device.connected ? "Connected" : device.status || "Disconnected";
            const actionKey = `connect:${device.id}`;
            const disconnectKey = `disconnect:${device.id}`;
            const mirrorKey = `${device.mirroring ? "mirror/stop" : "mirror/start"}:${device.id}`;
            const screenshotKey = `screenshot:${device.id}`;

            return (
              <article className="device-card" key={device.id}>
                <div className="device-topline">
                  <div className="device-icon">{icon}</div>
                  <div>
                    <h3>{device.name || device.address || device.adb_serial}</h3>
                    <p>{device.address || device.adb_serial}</p>
                  </div>
                  <span className={`status-pill ${device.connected ? "online" : "idle"}`}>{stateText}</span>
                </div>

                <div className="device-actions">
                  {onConnect ? (
                    <button
                      className="ghost-button"
                      disabled={busyKey === actionKey || device.connected}
                      onClick={() => onConnect(device)}
                    >
                      <Link2 size={15} />
                      Connect
                    </button>
                  ) : null}
                  {onDisconnect ? (
                    <button
                      className="ghost-button"
                      disabled={busyKey === disconnectKey || !device.connected}
                      onClick={() => onDisconnect(device)}
                    >
                      <Link2Off size={15} />
                      Disconnect
                    </button>
                  ) : null}
                  <button
                    className="ghost-button"
                    disabled={busyKey === mirrorKey || (!device.connected && device.type !== "usb")}
                    onClick={() => onMirror(device)}
                  >
                    <Monitor size={15} />
                    {device.mirroring ? "Stop Mirror" : "Mirror"}
                  </button>
                  <button
                    className="ghost-button"
                    disabled={busyKey === screenshotKey || !device.connected}
                    onClick={() => onScreenshot(device)}
                  >
                    <Camera size={15} />
                    Screenshot
                  </button>
                </div>
              </article>
            );
          })
        )}
      </div>
    </div>
  );
}

export default App;
