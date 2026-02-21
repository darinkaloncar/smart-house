import React from "react";
import "./styles.css";

const GRAFANA_BASE =
  "http://localhost:3000/d-solo/adwr22k/smart-house?orgId=1&from=now-1h&to=now&refresh=1s&timezone=browser";

const panelSrc = (panelId, category = "State%20timeline") =>
  `${GRAFANA_BASE}&showCategory=${category}&panelId=${panelId}`;

function GrafanaPanel({ title, panelId, height = 200, category }) {
  return (
    <div className="grafana-wrap">
      <h2>{title}</h2>
      <iframe
        src={panelSrc(panelId, category)}
        className="grafana-frame"
        style={{ height }}
        frameBorder="0"
        title={title}
      />
    </div>
  );
}

/**
 * Pi2Tab
 * NOTE:
 * - Replace panelId values with your actual Grafana panel IDs for PI2.
 * - For 4SD / DHT3 / GSG you may want different chart types (Time series / Table).
 */
export default function Pi2Tab() {
  return (
    <div className="grid two-cols">
      {/* DS2 */}
      <section className="card">
        <GrafanaPanel title="DS2 - Door Sensor (Button)" panelId={21} />
      </section>

      {/* DUS2 */}
      <section className="card">
        <GrafanaPanel title="DUS2 - Door Ultrasonic Sensor" panelId={22} />
      </section>

      {/* DPIR2 */}
      <section className="card">
        <GrafanaPanel title="DPIR2 - Door Motion Sensor" panelId={23} />
      </section>

      {/* 4SD */}
      <section className="card">
        <GrafanaPanel
          title="4SD - Kitchen 4 Digit 7 Segment Display Timer"
          panelId={24}
          // category="Time%20series" // uncomment if this panel is time-series
        />
      </section>

      {/* BTN */}
      <section className="card">
        <GrafanaPanel title="BTN - Kitchen Button" panelId={25} />
      </section>

      {/* DHT3 */}
      <section className="card">
        <GrafanaPanel
          title="DHT3 - Kitchen DHT"
          panelId={26}
          // category="Time%20series" // likely better for temperature/humidity
          height={220}
        />
      </section>

      {/* GSG */}
      <section className="card">
        <GrafanaPanel
          title="GSG - Gyroscope"
          panelId={27}
          // category="Time%20series" // likely better for gyro axes
          height={220}
        />
      </section>
    </div>
  );
}
