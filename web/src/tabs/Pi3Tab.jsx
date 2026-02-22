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
 * Pi3Tab
 * Zameni panelId vrednosti stvarnim ID-jevima iz Grafane.
 * Preporuka:
 * - DPIR3 / IR / BRGB: State timeline
 * - DHT1 / DHT2: Time series
 * - LCD: Table (ili Time series ako upisuješ numeric value)
 */
export default function Pi3Tab() {
  return (
    <div className="grid two-cols">
      {/* DHT1 */}
      <section className="card">
        <GrafanaPanel
          title="DHT1 - Bedroom DHT"
          panelId={31}
          // category="Time%20series"
          height={220}
        />
      </section>

      {/* DHT2 */}
      <section className="card">
        <GrafanaPanel
          title="DHT2 - Master Bedroom DHT"
          panelId={32}
          // category="Time%20series"
          height={220}
        />
      </section>

      {/* IR */}
      <section className="card">
        <GrafanaPanel title="IR - Bedroom Infrared" panelId={33} />
      </section>

      {/* BRGB */}
      <section className="card">
        <GrafanaPanel title="BRGB - Bedroom RGB" panelId={34} />
      </section>

      {/* LCD */}
      <section className="card">
        <GrafanaPanel
          title="LCD - Living Room Display"
          panelId={35}
          // category="Table"
          height={220}
        />
      </section>

      {/* DPIR3 */}
      <section className="card">
        <GrafanaPanel title="DPIR3 - Living Room Motion Sensor" panelId={36} />
      </section>
    </div>
  );
}
