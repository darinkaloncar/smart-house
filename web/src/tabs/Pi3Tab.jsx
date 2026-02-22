import React from "react";
import "./styles.css";

const GRAFANA_BASE =
  "http://localhost:3000/d-solo/advhvp6/new-dashboard?orgId=1&from=now-1h&to=now&refresh=1s&timezone=browser&__feature.dashboardSceneSolo=true";

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

export default function Pi3Tab() {
  return (
    <div className="grid two-cols">
      {/* DHT1 */}
      <section className="card">
        <GrafanaPanel
          title="DHT1 - Bedroom DHT"
          panelId="panel-1"
          height={220}
        />
      </section>

      {/* DHT2 */}
      <section className="card">
        <GrafanaPanel
          title="DHT2 - Master Bedroom DHT"
          panelId="panel-2"
          height={220}
        />
      </section>

      {/* IR */}
      <section className="card">
        <GrafanaPanel title="IR - Bedroom Infrared" panelId="panel-3" />
      </section>

      {/* BRGB */}
      <section className="card">
        <GrafanaPanel title="BRGB - Bedroom RGB" panelId="panel-4" />
      </section>

      {/* DPIR3 */}
      <section className="card">
        <GrafanaPanel
          title="DPIR3 - Living Room Motion Sensor"
          panelId="panel-5"
        />
      </section>
      {/* LCD */}
      <section className="card">
        <div className="grafana-wrap">
          <h2>LCD - Living Room Display</h2>
          <div className="tiny">TODO</div>
        </div>
      </section>
    </div>
  );
}
