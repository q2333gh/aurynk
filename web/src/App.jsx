import {
  Camera,
  Link2,
  Link2Off,
  Monitor,
  Plus,
  RefreshCw,
  Settings,
  Smartphone,
  Usb,
  X,
} from "lucide-react";
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
  const [settingsDrawerOpen, setSettingsDrawerOpen] = useState(false);
  const [pairingPanelOpen, setPairingPanelOpen] = useState(false);
  const [manualPairingOpen, setManualPairingOpen] = useState(false);
  const [showSetupSettings, setShowSetupSettings] = useState(false);
  const [showAdvancedSettings, setShowAdvancedSettings] = useState(false);

  const groupedDevices = useMemo(
    () => ({
      wireless: devices.filter((device) => device.type === "wireless"),
      usb: devices.filter((device) => device.type === "usb"),
    }),
    [devices],
  );

  const hasDevices = devices.length > 0;
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
      setManualPairingOpen(false);
      if (hasDevices) {
        setPairingPanelOpen(false);
      }
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
      setPairingPanelOpen(true);
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
      setSettingsDrawerOpen(false);
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

  function togglePairingPanel() {
    setPairingPanelOpen((value) => !value);
    if (!pairingPanelOpen) {
      setManualPairingOpen(false);
    }
  }

  return (
    <div className="app-shell">
      <div className="ambient ambient-a" />
      <div className="ambient ambient-b" />

      <header className="topbar">
        <div className="topbar-actions">
          <button className="primary-button" type="button" onClick={togglePairingPanel}>
            <Plus size={16} />
            {pairingPanelOpen ? "Hide" : "Add Device"}
          </button>
          <button className="ghost-button" onClick={loadDevices}>
            <RefreshCw size={16} />
            Refresh
          </button>
          <button className="ghost-button" onClick={() => setSettingsDrawerOpen(true)}>
            <Settings size={16} />
            Settings
          </button>
        </div>
      </header>

      {error ? <div className="banner banner-error">{error}</div> : null}
      {notice ? <div className="banner banner-ok">{notice}</div> : null}

      <main className="layout layout-single">
        <section className="primary-column">
          <div className="hero-strip">
            <div className="hero-metrics">
              <div className="hero-stat">
                <span className="hero-stat-value">{devices.length}</span>
                <span className="hero-stat-label">All</span>
              </div>
              <div className="hero-stat">
                <span className="hero-stat-value">{groupedDevices.wireless.length}</span>
                <span className="hero-stat-label">Wi-Fi</span>
              </div>
              <div className="hero-stat">
                <span className="hero-stat-value">{groupedDevices.usb.length}</span>
                <span className="hero-stat-label">USB</span>
              </div>
            </div>
          </div>

          {!hasDevices ? (
            <div className="panel onboarding-panel">
              <div className="empty-state compact-empty-state">
                <h2>No devices</h2>
                {!pairingPanelOpen ? (
                  <button className="primary-button" type="button" onClick={togglePairingPanel}>
                    <Plus size={16} />
                    Add Device
                  </button>
                ) : null}
              </div>
            </div>
          ) : null}

          {pairingPanelOpen ? (
            <div className="panel pairing-panel">
              <div className="panel-header compact-panel-header">
                <div>
                  <h2>Pair device</h2>
                </div>
                {hasDevices ? (
                  <button className="icon-button" type="button" onClick={() => setPairingPanelOpen(false)}>
                    <X size={16} />
                  </button>
                ) : null}
              </div>

              <div className="pairing-card">
                <div className="pairing-copy">
                  <h3>QR</h3>
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
                    <button
                      className="ghost-button"
                      type="button"
                      onClick={() => setManualPairingOpen((value) => !value)}
                    >
                      {manualPairingOpen ? "Hide Manual Pairing" : "Manual Pairing"}
                    </button>
                  </div>
                  <p className="qr-status">
                    {qrPairing.message || "Ready"}
                  </p>
                </div>
                <div className="qr-card compact-qr-card">
                  {qrPairing.active && qrPairing.qr_image_data_url ? (
                    <img className="qr-image" src={qrPairing.qr_image_data_url} alt="Aurynk QR pairing code" />
                  ) : (
                    <div className="qr-placeholder">No QR</div>
                  )}
                </div>
              </div>

              {manualPairingOpen ? (
                <form className="pair-grid compact-pair-grid" onSubmit={handlePair}>
                  <label>
                    <span>Address</span>
                    <input
                      value={pairForm.address}
                      onChange={(event) =>
                        setPairForm((current) => ({ ...current, address: event.target.value }))
                      }
                      placeholder="192.168.1.10"
                    />
                  </label>
                  <label>
                    <span>Pair Port</span>
                    <input
                      value={pairForm.pair_port}
                      onChange={(event) =>
                        setPairForm((current) => ({ ...current, pair_port: event.target.value }))
                      }
                      placeholder="38123"
                    />
                  </label>
                  <label>
                    <span>Connect Port</span>
                    <input
                      value={pairForm.connect_port}
                      onChange={(event) =>
                        setPairForm((current) => ({ ...current, connect_port: event.target.value }))
                      }
                      placeholder="34891"
                    />
                  </label>
                  <label>
                    <span>Password</span>
                    <input
                      value={pairForm.password}
                      onChange={(event) =>
                        setPairForm((current) => ({ ...current, password: event.target.value }))
                      }
                      placeholder="123456"
                    />
                  </label>
                  <button className="primary-button pair-submit" type="submit" disabled={busyKey === "pair"}>
                    {busyKey === "pair" ? "Pairing..." : "Pair and Connect"}
                  </button>
                </form>
              ) : null}
            </div>
          ) : null}

          <DeviceSection
            title="Wireless"
            kicker="Paired"
            icon={<Smartphone size={16} />}
            devices={groupedDevices.wireless}
            busyKey={busyKey}
            onConnect={(device) => runDeviceAction("connect", device, { address: device.address })}
            onDisconnect={(device) =>
              runDeviceAction("disconnect", device, { address: device.address })
            }
            onMirror={(device) =>
              runDeviceAction(device.mirroring ? "mirror/stop" : "mirror/start", device)
            }
            onScreenshot={(device) => runDeviceAction("screenshot", device)}
          />

          <DeviceSection
            title="USB"
            kicker="ADB"
            icon={<Usb size={16} />}
            devices={groupedDevices.usb}
            busyKey={busyKey}
            onMirror={(device) =>
              runDeviceAction(device.mirroring ? "mirror/stop" : "mirror/start", device)
            }
            onScreenshot={(device) => runDeviceAction("screenshot", device)}
          />
        </section>
      </main>

      <SettingsDrawer
        open={settingsDrawerOpen}
        settings={settings}
        busyKey={busyKey}
        showSetupSettings={showSetupSettings}
        showAdvancedSettings={showAdvancedSettings}
        onClose={() => setSettingsDrawerOpen(false)}
        onSave={saveSettings}
        onToggleSetup={() => setShowSetupSettings((value) => !value)}
        onToggleAdvanced={() => setShowAdvancedSettings((value) => !value)}
        onUpdateSetting={updateSetting}
      />
    </div>
  );
}

function SettingsDrawer({
  open,
  settings,
  busyKey,
  showSetupSettings,
  showAdvancedSettings,
  onClose,
  onSave,
  onToggleSetup,
  onToggleAdvanced,
  onUpdateSetting,
}) {
  return (
    <>
      <div className={`drawer-backdrop ${open ? "visible" : ""}`} onClick={onClose} />
      <aside className={`settings-drawer ${open ? "open" : ""}`}>
        <div className="drawer-header">
          <div>
            <h2>Settings</h2>
          </div>
          <button className="icon-button" type="button" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        <div className="drawer-body">
          <div className="settings-group">
            <h3>General</h3>
            <label className="toggle-row">
              <span>Show notifications</span>
              <input
                type="checkbox"
                checked={Boolean(settings.app?.show_notifications)}
                onChange={(event) =>
                  onUpdateSetting("app", "show_notifications", event.target.checked)
                }
              />
            </label>
            <label className="toggle-row">
              <span>Always on top</span>
              <input
                type="checkbox"
                checked={Boolean(settings.scrcpy?.always_on_top)}
                onChange={(event) =>
                  onUpdateSetting("scrcpy", "always_on_top", event.target.checked)
                }
              />
            </label>
            <label className="toggle-row">
              <span>Enable audio</span>
              <input
                type="checkbox"
                checked={Boolean(settings.scrcpy?.enable_audio)}
                onChange={(event) =>
                  onUpdateSetting("scrcpy", "enable_audio", event.target.checked)
                }
              />
            </label>
          </div>

          <div className="settings-fold">
            <button className="fold-toggle" type="button" onClick={onToggleSetup}>
              <span>Setup</span>
              <span>{showSetupSettings ? "Hide" : "Show"}</span>
            </button>
            {showSetupSettings ? (
              <div className="settings-group settings-group-subtle">
                <label className="field-row">
                  <span>ADB path</span>
                  <input
                    value={settings.adb?.adb_path ?? ""}
                    onChange={(event) => onUpdateSetting("adb", "adb_path", event.target.value)}
                    placeholder="C:\\Android\\platform-tools\\adb.exe or C:\\Android\\platform-tools"
                  />
                </label>
                <label className="field-row">
                  <span>scrcpy path</span>
                  <input
                    value={settings.scrcpy?.scrcpy_path ?? ""}
                    onChange={(event) =>
                      onUpdateSetting("scrcpy", "scrcpy_path", event.target.value)
                    }
                    placeholder="C:\\Tools\\scrcpy\\scrcpy.exe or C:\\Tools\\scrcpy"
                  />
                </label>
              </div>
            ) : null}
          </div>

          <div className="settings-fold">
            <button className="fold-toggle" type="button" onClick={onToggleAdvanced}>
              <span>Advanced</span>
              <span>{showAdvancedSettings ? "Hide" : "Show"}</span>
            </button>
            {showAdvancedSettings ? (
              <div className="settings-group settings-group-subtle">
                <label className="field-row">
                  <span>Theme</span>
                  <select
                    value={settings.app?.theme || "system"}
                    onChange={(event) => onUpdateSetting("app", "theme", event.target.value)}
                  >
                    <option value="system">System</option>
                    <option value="light">Light</option>
                    <option value="dark">Dark</option>
                  </select>
                </label>
                <label className="field-row">
                  <span>Connection timeout</span>
                  <input
                    type="number"
                    value={settings.adb?.connection_timeout ?? 10}
                    onChange={(event) =>
                      onUpdateSetting("adb", "connection_timeout", Number(event.target.value))
                    }
                  />
                </label>
                <label className="field-row">
                  <span>Retry attempts</span>
                  <input
                    type="number"
                    value={settings.adb?.max_retry_attempts ?? 5}
                    onChange={(event) =>
                      onUpdateSetting("adb", "max_retry_attempts", Number(event.target.value))
                    }
                  />
                </label>
                <label className="field-row">
                  <span>Video bitrate (Mbps)</span>
                  <input
                    type="number"
                    value={settings.scrcpy?.video_bitrate ?? 8}
                    onChange={(event) =>
                      onUpdateSetting("scrcpy", "video_bitrate", Number(event.target.value))
                    }
                  />
                </label>
                <label className="field-row">
                  <span>Max FPS</span>
                  <input
                    type="number"
                    value={settings.scrcpy?.max_fps ?? 0}
                    onChange={(event) =>
                      onUpdateSetting("scrcpy", "max_fps", Number(event.target.value))
                    }
                  />
                </label>
              </div>
            ) : null}
          </div>
        </div>

        <div className="drawer-footer">
          <button className="primary-button wide" disabled={busyKey === "save-settings"} onClick={onSave}>
            {busyKey === "save-settings" ? "Saving..." : "Save Settings"}
          </button>
        </div>
      </aside>
    </>
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
    <div className="panel compact-panel">
      <div className="panel-header compact-panel-header">
        <div>
          <h2>{title}</h2>
        </div>
      </div>

      <div className="device-grid compact-device-grid">
        {devices.length === 0 ? (
          <div className="empty-state slim-empty-state">Empty</div>
        ) : (
          devices.map((device) => {
            const stateText = device.connected ? "Connected" : device.status || "Disconnected";
            const actionKey = `connect:${device.id}`;
            const disconnectKey = `disconnect:${device.id}`;
            const mirrorKey = `${device.mirroring ? "mirror/stop" : "mirror/start"}:${device.id}`;
            const screenshotKey = `screenshot:${device.id}`;

            return (
              <article className="device-card compact-device-card" key={device.id}>
                <div className="device-topline compact-device-topline">
                  <div className="device-icon compact-device-icon">{icon}</div>
                  <div className="device-meta">
                    <h3>{device.name || device.address || device.adb_serial}</h3>
                    <p>{device.address || device.adb_serial}</p>
                  </div>
                  <span className={`status-pill ${device.connected ? "online" : "idle"}`}>{stateText}</span>
                </div>

                <div className="device-actions compact-device-actions">
                  {onConnect && !device.connected ? (
                    <button className="ghost-button" disabled={busyKey === actionKey} onClick={() => onConnect(device)}>
                      <Link2 size={14} />
                      Connect
                    </button>
                  ) : null}
                  <button
                    className="ghost-button"
                    disabled={busyKey === mirrorKey || (!device.connected && device.type !== "usb")}
                    onClick={() => onMirror(device)}
                  >
                    <Monitor size={14} />
                    {device.mirroring ? "Stop Mirror" : "Mirror"}
                  </button>
                  <button
                    className="ghost-button"
                    disabled={busyKey === screenshotKey || !device.connected}
                    onClick={() => onScreenshot(device)}
                  >
                    <Camera size={14} />
                    Screenshot
                  </button>
                  {onDisconnect && device.connected ? (
                    <button className="ghost-button" disabled={busyKey === disconnectKey} onClick={() => onDisconnect(device)}>
                      <Link2Off size={14} />
                      Disconnect
                    </button>
                  ) : null}
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
