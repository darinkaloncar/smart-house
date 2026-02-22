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

export default function Pi1Tab() {
  return (
    <div className="grid two-cols">
      <section className="card">
        <GrafanaPanel title="DS1 - Door Sensor" panelId={2} />
      </section>

      <section className="card">
        <GrafanaPanel title="DL - Door Light" panelId={4} />
      </section>

      <section className="card">
        <GrafanaPanel title="DUS1 - Door Ultrasonic Sensor" panelId={1} />
      </section>

      <section className="card">
        <GrafanaPanel title="DB - Door Buzzer" panelId={5} />
      </section>

      <section className="card">
        <GrafanaPanel title="DPIR1 - Door Motion Sensor" panelId={3} />
      </section>

      <section className="card">
        <GrafanaPanel title="DMS - Door Membrane Switch" panelId={6} />
      </section>

      <section className="card no-chart">
        <h2>WEBC - Door Web Camera</h2>

        <div className="camera-wrap">
          <img
            src="http://<raspberry_pi_ip>:8080/?action=stream"
            alt="Door camera stream"
            className="camera-stream"
          />
        </div>
      </section>
    </div>
  );
}
