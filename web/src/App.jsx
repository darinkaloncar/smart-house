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
  sendDmsKey,
  setRgbColor,
  setTimer,
  timerAdd,
  kitchenBtnPressed,
} from "./api";

const BRGB_OPTIONS = [
  "off",
  "white",
  "red",
  "green",
  "blue",
  "yellow",
  "purple",
  "lightBlue",
];

const BRGB_PREVIEW = {
  off: "rgb(0,0,0)",
  white: "rgb(255,255,255)",
  red: "rgb(255,0,0)",
  green: "rgb(0,255,0)",
  blue: "rgb(0,0,255)",
  yellow: "rgb(255,255,0)",
  purple: "rgb(255,0,255)",
  lightBlue: "rgb(0,255,255)",
};

function App() {
  const [status, setStatus] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");

  const [activeTab, setActiveTab] = useState("overview");

  const [pinInput, setPinInput] = useState("");
  const [timerSecondsInput, setTimerSecondsInput] = useState(90);
  const [timerAddNInput, setTimerAddNInput] = useState(10);

  const [selectedBrgbColor, setSelectedBrgbColor] = useState("off");

  const dmsKeys = [
    ["1", "2", "3", "A"],
    ["4", "5", "6", "B"],
    ["7", "8", "9", "C"],
    ["*", "0", "#", "D"],
  ];

  const handleKeyClick = (key) => {
    if (key === "*") {
      setPinInput("");
      return;
    }

    if (key === "#") {
      sendPin(); // enter / submit
      return;
    }

    if (!/^[0-9A-D]$/i.test(key)) return;

    setPinInput((prev) => (prev + key.toUpperCase()).slice(0, 8));
  };

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

  useEffect(() => {
    const backendColor = status?.brgb_color;
    if (
      typeof backendColor === "string" &&
      BRGB_OPTIONS.includes(backendColor)
    ) {
      setSelectedBrgbColor(backendColor);
    } else if (status?.brgb_on === false) {
      setSelectedBrgbColor("off");
    }
  }, [status?.brgb_color, status?.brgb_on]);

  const boolClass = (v) => (v ? "pill on" : "pill off");

  const formatTimer = (seconds) => {
    const s = Number(seconds ?? 0);
    const mm = Math.floor(s / 60);
    const ss = s % 60;
    return `${String(mm).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
  };

  const sensor = (name) => status?.sensors?.[name];

  const rgbPreview = useMemo(() => {
    const backendColor = status?.brgb_color;

    if (typeof backendColor === "string" && BRGB_PREVIEW[backendColor]) {
      return BRGB_PREVIEW[backendColor];
    }

    if (
      backendColor &&
      typeof backendColor === "object" &&
      "r" in backendColor &&
      "g" in backendColor &&
      "b" in backendColor
    ) {
      return `rgb(${backendColor.r || 0}, ${backendColor.g || 0}, ${backendColor.b || 0})`;
    }

    return BRGB_PREVIEW[selectedBrgbColor] || BRGB_PREVIEW.off;
  }, [status, selectedBrgbColor]);

  const call = async (fn) => {
    try {
      await fn();
      await loadStatus();
    } catch (e) {
      console.error(e);
    }
  };

  const sendPin = async () => {
    const pin = (pinInput || "").trim();
    console.log("[UI] sendPin pin=", pin);

    if (!pin) return;

    try {
      for (const ch of pin) {
        console.log("[UI] sending dms key:", ch);
        await sendDmsKey(ch);
      }
      setPinInput("");
      await loadStatus();
    } catch (e) {
      console.error("[UI] sendPin error", e);
    }
  };

  const handleBrgbChange = async (e) => {
    const color = e.target.value;

    setSelectedBrgbColor(color);

    try {
      await setRgbColor(color);
      await loadStatus();
    } catch (err) {
      console.error(err);
    }
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
            <span>PIN set:</span>
            <span className={boolClass(status?.pin_set)}>
              {status?.pin_set ? "DA" : "NE"}
            </span>
          </div>

          <div className="row">
            <span>Arming in:</span>
            <strong>
              {status?.arming_pending
                ? Math.max(
                    0,
                    Math.ceil(status.arming_until - Date.now() / 1000),
                  ) + "s"
                : "-"}
            </strong>
          </div>

          <div className="row">
            <span>Entry in:</span>
            <strong>
              {status?.entry_pending
                ? Math.max(
                    0,
                    Math.ceil(status.entry_until - Date.now() / 1000),
                  ) + "s"
                : "-"}
            </strong>
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

          <div className="dms-grid">
            {dmsKeys.map((row, rowIndex) =>
              row.map((key) => (
                <button
                  key={`${rowIndex}-${key}`}
                  onClick={() => handleKeyClick(key)}
                  className="dms-key"
                >
                  {key}
                </button>
              )),
            )}
          </div>
        </section>

        {/* TIMER */}
        <section className="card">
          <h2>Kuhinjska štoperica</h2>

          <div className="row">
            <span>Timer:</span>
            <div className="timer-row">
              <strong>{String(status?.timer_seconds ?? "00:00")}</strong>
            </div>
          </div>

          {/* 1) Set timer seconds */}
          <div className="row">
            <input
              type="number"
              value={timerSecondsInput}
              onChange={(e) => setTimerSecondsInput(e.target.value)}
              placeholder="npr. 90"
            />
            <button
              onClick={() =>
                call(() => setTimer(Number(timerSecondsInput) || 0))
              }
            >
              Set seconds
            </button>
          </div>

          {/* 2) Add seconds button press */}
          <div className="row">
            <input
              type="number"
              value={timerAddNInput}
              onChange={(e) => setTimerAddNInput(e.target.value)}
              placeholder="npr. 10"
            />
            <button
              onClick={() => call(() => timerAdd(Number(timerAddNInput) || 0))}
            >
              Set add seconds
            </button>
          </div>
          {/* 2) Kitchen button press */}
          <div className="row">
            <button onClick={() => call(() => kitchenBtnPressed())}>
              Kitchen button
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
            <label htmlFor="brgb-color">Boja</label>
            <select
              id="brgb-color"
              value={selectedBrgbColor}
              onChange={handleBrgbChange}
            >
              {BRGB_OPTIONS.map((color) => (
                <option key={color} value={color}>
                  {color}
                </option>
              ))}
            </select>
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
      </div>
    );
  };

  return (
    <div className="container">
      <h1>Smart Home Dashboard</h1>
      <div className="tiny">Backend: http://localhost:5001</div>

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
