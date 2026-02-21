import { useEffect, useMemo, useState } from "react";
import "./App.css";
import Pi1Tab from "./tabs/Pi1Tab";
import Pi2Tab from "./tabs/Pi2Tab";
import Pi3Tab from "./tabs/Pi3Tab";

import {
  alarmOff,
  alarmOn,
  armSystem,
  disarmSystem,
  getStatus,
  scenarioPi1Entry,
  scenarioPi1Exit,
  sendDmsKey,
  setRgb,
  setTimer,
  setTimerAddN,
  timerAdd,
} from "./api";

function App() {
  const [status, setStatus] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");

  const [activeTab, setActiveTab] = useState("overview");

  const [pinInput, setPinInput] = useState("");
  const [timerSecondsInput, setTimerSecondsInput] = useState(90);
  const [timerAddNInput, setTimerAddNInput] = useState(10);

  const [rgb, setRgbState] = useState({ r: 255, g: 0, b: 0 });

  const loadStatus = async () => {
    try {
      const res = await getStatus();
      setStatus(res.data);
      setErrorMsg("");
    } catch (err) {
      console.error(err);
      setErrorMsg("Ne mogu da učitam status backend-a.");
    }
  };

  useEffect(() => {
    loadStatus();
    const id = setInterval(loadStatus, 1000); // polling 1s
    return () => clearInterval(id);
  }, []);

  const boolClass = (v) => (v ? "pill on" : "pill off");

  const formatTimer = (seconds) => {
    const s = Number(seconds ?? 0);
    const mm = Math.floor(s / 60);
    const ss = s % 60;
    return `${String(mm).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
  };

  const sensor = (name) => status?.sensors?.[name];

  const rgbPreview = useMemo(() => {
    const c = status?.brgb_color || rgb;
    return `rgb(${c?.r || 0}, ${c?.g || 0}, ${c?.b || 0})`;
  }, [status, rgb]);

  const call = async (fn) => {
    try {
      await fn();
      loadStatus();
    } catch (e) {
      console.error(e);
    }
  };

  const sendPin = async () => {
    const pin = (pinInput || "").trim();
    if (!pin) return;
    try {
      for (const ch of pin) {
        await sendDmsKey(ch);
      }
      setPinInput("");
      loadStatus();
    } catch (e) {
      console.error(e);
    }
  };

  const applyRgb = async () => {
    await call(() =>
      setRgb({
        r: Number(rgb.r) || 0,
        g: Number(rgb.g) || 0,
        b: Number(rgb.b) || 0,
      }),
    );
  };

  const renderTabContent = () => {
    if (activeTab === "pi1") {
      return <Pi1Tab status={status} sensor={sensor} boolClass={boolClass} />;
    }

    if (activeTab === "pi2") {
      return <Pi2Tab status={status} sensor={sensor} boolClass={boolClass} />;
    }

    if (activeTab === "pi3") {
      return <Pi3Tab status={status} sensor={sensor} boolClass={boolClass} />;
    }

    // OVERVIEW
    return (
      <div className="grid">
        {/* STATUS */}
        <section className="card">
          <h2>Status sistema</h2>

          <div className="row">
            <span>Alarm:</span>
            <span className={boolClass(status?.alarm_on)}>
              {status?.alarm_on ? "ON" : "OFF"}
            </span>
          </div>

          <div className="row">
            <span>Sistem armed:</span>
            <span className={boolClass(status?.system_armed)}>
              {status?.system_armed ? "DA" : "NE"}
            </span>
          </div>

          <div className="row">
            <span>Arming pending:</span>
            <span className={boolClass(status?.arming_pending)}>
              {status?.arming_pending ? "DA" : "NE"}
            </span>
          </div>

          <div className="row">
            <span>People count:</span>
            <strong>{status?.people_count ?? 0}</strong>
          </div>

          <div className="row">
            <span>DL1:</span>
            <span className={boolClass(status?.dl1_on)}>
              {status?.dl1_on ? "ON" : "OFF"}
            </span>
          </div>

          <div className="row buttons">
            <button onClick={() => call(() => alarmOn())}>
              Alarm ON (test)
            </button>
            <button onClick={() => call(() => alarmOff())}>Alarm OFF</button>
          </div>

          <div className="row buttons">
            <button onClick={() => call(() => armSystem())}>Arm system</button>
            <button onClick={() => call(() => disarmSystem())}>
              Disarm system
            </button>
          </div>
        </section>

        {/* DMS / PIN */}
        <section className="card">
          <h2>DMS / PIN</h2>

          <div className="row">
            <input
              type="text"
              maxLength={8}
              placeholder="2110"
              value={pinInput}
              onChange={(e) => setPinInput(e.target.value)}
            />
            <button onClick={sendPin}>Pošalji PIN</button>
          </div>

          <div className="row buttons">
            {["1", "2", "3", "4"].map((k) => (
              <button key={k} onClick={() => call(() => sendDmsKey(k))}>
                {k}
              </button>
            ))}
            <button onClick={() => call(() => sendDmsKey("*"))}>*</button>
            <button onClick={() => call(() => sendDmsKey("#"))}>#</button>
          </div>
        </section>

        {/* TIMER */}
        <section className="card">
          <h2>Kuhinjska štoperica</h2>

          <div className="row">
            <span>Timer:</span>
            <strong>{formatTimer(status?.timer_seconds)}</strong>
            <span className={boolClass(status?.timer_blink)}>
              blink: {status?.timer_blink ? "DA" : "NE"}
            </span>
          </div>

          <div className="row">
            <input
              type="number"
              value={timerSecondsInput}
              onChange={(e) => setTimerSecondsInput(e.target.value)}
            />
            <button
              onClick={() =>
                call(() => setTimer(Number(timerSecondsInput) || 0))
              }
            >
              Set seconds
            </button>
          </div>

          <div className="row">
            <input
              type="number"
              value={timerAddNInput}
              onChange={(e) => setTimerAddNInput(e.target.value)}
            />
            <button
              onClick={() =>
                call(() => setTimerAddN(Number(timerAddNInput) || 1))
              }
            >
              Set BTN +N
            </button>
          </div>

          <div className="row buttons">
            <button onClick={() => call(() => timerAdd())}>
              BTN Add / Stop Blink
            </button>
          </div>
        </section>

        {/* RGB */}
        <section className="card">
          <h2>BRGB</h2>

          <div className="row">
            <span>Stanje:</span>
            <span className={boolClass(status?.brgb_on)}>
              {status?.brgb_on ? "ON" : "OFF"}
            </span>
            <span className="color-box" style={{ background: rgbPreview }} />
          </div>

          <div className="row">
            <label>R</label>
            <input
              type="number"
              min="0"
              max="255"
              value={rgb.r}
              onChange={(e) =>
                setRgbState((p) => ({ ...p, r: e.target.value }))
              }
            />
            <label>G</label>
            <input
              type="number"
              min="0"
              max="255"
              value={rgb.g}
              onChange={(e) =>
                setRgbState((p) => ({ ...p, g: e.target.value }))
              }
            />
            <label>B</label>
            <input
              type="number"
              min="0"
              max="255"
              value={rgb.b}
              onChange={(e) =>
                setRgbState((p) => ({ ...p, b: e.target.value }))
              }
            />
          </div>

          <div className="row buttons">
            <button onClick={() => call(() => setRgb({ on: true }))}>
              RGB ON
            </button>
            <button onClick={() => call(() => setRgb({ on: false }))}>
              RGB OFF
            </button>
            <button onClick={applyRgb}>Primeni boju</button>
          </div>
        </section>

        {/* SCENARIOS */}
        <section className="card">
          <h2>Manual scenariji (DPIR + DUS)</h2>
          <div className="row buttons">
            <button onClick={() => call(() => scenarioPi1Entry())}>
              PI1 ENTRY
            </button>
            <button onClick={() => call(() => scenarioPi1Exit())}>
              PI1 EXIT
            </button>
          </div>
          <div className="tiny">
            Ovi scenariji šalju smislen DUS niz + DPIR okidanje da people_count
            radi pouzdanije.
          </div>
        </section>

        {/* SENSORS */}
        <section className="card">
          <h2>Senzori (trenutno stanje)</h2>
          <div className="sensors">
            <div>
              <b>DS1:</b> {String(sensor("DS1"))}
            </div>
            <div>
              <b>DS2:</b> {String(sensor("DS2"))}
            </div>
            <div>
              <b>DPIR1:</b> {String(sensor("DPIR1"))}
            </div>
            <div>
              <b>DPIR2:</b> {String(sensor("DPIR2"))}
            </div>
            <div>
              <b>DPIR3:</b> {String(sensor("DPIR3"))}
            </div>
            <div>
              <b>DUS1:</b> {String(sensor("DUS1"))}
            </div>
            <div>
              <b>DUS2:</b> {String(sensor("DUS2"))}
            </div>
            <div>
              <b>GSG:</b> {String(sensor("GSG"))}
            </div>
          </div>
          <div className="mono">
            DHT1: T={String(sensor("DHT1")?.temp)} H=
            {String(sensor("DHT1")?.hum)}
            {"\n"}
            DHT2: T={String(sensor("DHT2")?.temp)} H=
            {String(sensor("DHT2")?.hum)}
            {"\n"}
            DHT3: T={String(sensor("DHT3")?.temp)} H=
            {String(sensor("DHT3")?.hum)}
          </div>
        </section>

        {/* NOTIFICATIONS */}
        <section className="card">
          <h2>Notifikacije</h2>
          <div className="notif-list">
            {(status?.notifications || [])
              .slice()
              .reverse()
              .map((n, i) => (
                <div key={i} className="notif-item">
                  <span className="time">{n.time}</span> — {n.message}
                </div>
              ))}
          </div>
        </section>
      </div>
    );
  };

  return (
    <div className="container">
      <h1>Smart Home Dashboard</h1>
      <div className="tiny">Backend: http://localhost:5000</div>

      {errorMsg && <div className="error">{errorMsg}</div>}

      <div className="tabs">
        <button
          className={activeTab === "overview" ? "tab active" : "tab"}
          onClick={() => setActiveTab("overview")}
        >
          Overview
        </button>

        <button
          className={activeTab === "pi1" ? "tab active" : "tab"}
          onClick={() => setActiveTab("pi1")}
        >
          PI1
        </button>

        <button
          className={activeTab === "pi2" ? "tab active" : "tab"}
          onClick={() => setActiveTab("pi2")}
        >
          PI2
        </button>

        <button
          className={activeTab === "pi3" ? "tab active" : "tab"}
          onClick={() => setActiveTab("pi3")}
        >
          PI3
        </button>
      </div>

      {renderTabContent()}
    </div>
  );
}

export default App;
