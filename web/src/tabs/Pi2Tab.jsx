import React from "react";
import "./styles.css";

const GRAFANA_BASE =
  "http://localhost:3000/d-solo/adl7sjw/pi2?orgId=1&from=now-1h&to=now&refresh=1s&timezone=browser&__feature.dashboardSceneSolo=true";

const panelSrc = (panelId) => `${GRAFANA_BASE}&panelId=${panelId}`;

function GrafanaPanel({ title, panelId, height = 200 }) {
  return (
    <div className="grafana-wrap">
      <h2>{title}</h2>
      <iframe
        src={panelSrc(panelId)}
        className="grafana-frame"
        style={{ height }}
        frameBorder="0"
        title={title}
      />
    </div>
  );
}

export default function Pi2Tab() {
  return (
    <div className="grid two-cols">
      {/* DS2 */}
      <section className="card">
        <GrafanaPanel title="DS2 - Door Sensor (Button)" panelId="panel-1" />
      </section>

      {/* DUS2 */}
      <section className="card">
        <GrafanaPanel title="DUS2 - Door Ultrasonic Sensor" panelId="panel-2" />
      </section>

      {/* DPIR2 */}
      <section className="card">
        <GrafanaPanel title="DPIR2 - Door Motion Sensor" panelId="panel-3" />
      </section>

      {/* 4SD */}
      <section className="card">
        <GrafanaPanel
          title="4SD - Kitchen 4 Digit 7 Segment Display Timer"
          panelId="panel-4"
          height={220}
        />
      </section>

      {/* BTN */}
      <section className="card">
        <GrafanaPanel title="BTN - Kitchen Button" panelId="panel-5" />
      </section>

      {/* DHT3 */}
      <section className="card">
        <GrafanaPanel
          title="DHT3 - Kitchen DHT"
          panelId="panel-6"
          height={240}
        />
      </section>

      {/* GSG */}
      <section className="card">
        <GrafanaPanel title="GSG - Gyroscope" panelId="panel-7" height={240} />
      </section>
    </div>
  );
}
