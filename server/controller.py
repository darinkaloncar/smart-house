from flask import Flask, jsonify, request
from flask_cors import CORS
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import paho.mqtt.client as mqtt
import json
import threading
import time

app = Flask(__name__)
CORS(
    app,
    resources={r"/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}},
    supports_credentials=False
)


# -----------------------------
# InfluxDB Configuration
# -----------------------------
token = "K4Q54mHR_djZ9c2iF36m2TTKHdItfU6okDIZi_D4PfS2uVJsPOvyACgISyDLb__U049H3k2PFMPekwaGH2EmRQ=="
org = "MyOrg"
url = "http://localhost:8086"
bucket = "iot-db"

influxdb_client = InfluxDBClient(url=url, token=token, org=org)

# -----------------------------
# MQTT topics (komande aktuatorima)
# -----------------------------
TOPIC_DL1_CMD = "home/actuators/dl1/cmd"

# -----------------------------
# Global state 
# -----------------------------
lock = threading.Lock()

state = {
    "people_count": 0,
    "sensors": {
        "DPIR1": 0,
        "DUS1": None,
    },
    "dus_history": [],  # [(ts, dist), ...]

    # DL1 auto-off logika (tačka 2)
    "dl1_on": False,
    "dl1_until": 0.0,
}


# -----------------------------
# Server helper functions
# -----------------------------
def mqtt_send(topic, payload: dict):
    try:
        mqtt_client.publish(topic, json.dumps(payload))
        print("MQTT SEND:", topic, payload)
    except Exception as e:
        print("MQTT SEND ERROR:", e)

def save_to_db(data):
    """
    Ocekivani payload (npr.):
    {
      "measurement": "Distance" / "Motion",
      "simulated": true,
      "runs_on": "PI1",
      "name": "DUS1" / "DPIR1",
      "value": 123.4 / 1
    }
    """
    try:
        if "measurement" not in data:
            return

        point = (
            Point(str(data["measurement"]))
            .tag("simulated", str(data.get("simulated", True)))
            .tag("runs_on", str(data.get("runs_on", "")))
            .tag("name", str(data.get("name", "")))
        )

        value = data.get("value", None)

        if isinstance(value, bool):
            point = point.field("value", value)
        elif isinstance(value, (int, float)):
            point = point.field("value", value)
        else:
            try:
                point = point.field("value", float(value))
            except Exception:
                point = point.field("value_text", str(value))

        write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)
        write_api.write(bucket=bucket, org=org, record=point)

    except Exception as e:
        print("INFLUX SAVE ERROR:", e)


def get_last_dus1_values_from_db(n=3, lookback_s=15):
    """
    Vraca poslednja N DUS1 merenja iz baze (hronoloski: najstarije do najnovije)
    payload:
      measurement = "Distance"
      tag name = "DUS1"
      tag runs_on = "PI1"
      field = "value"
    """
    try:
        query_api = influxdb_client.query_api()
        flux = f'''
from(bucket: "{bucket}")
  |> range(start: -{int(lookback_s)}s)
  |> filter(fn: (r) => r._measurement == "Distance")
  |> filter(fn: (r) => r.name == "DUS1")
  |> filter(fn: (r) => r.runs_on == "PI1")
  |> filter(fn: (r) => r._field == "value")
  |> sort(columns: ["_time"], desc: false)
  |> tail(n: {int(n)})
'''
        tables = query_api.query(flux, org=org)

        values = []
        for table in tables:
            for record in table.records:
                try:
                    values.append(float(record.get_value()))
                except Exception:
                    pass

        return values
    except Exception as e:
        print("INFLUX QUERY ERROR:", e)
        return []


def infer_entry_exit_from_dus1():
    """
    Tacka 3:
      enter = distance opada
      exit  = distance raste
    """
    values = get_last_dus1_values_from_db(n=3, lookback_s=15)

    if len(values) < 3:
        with lock:
            if len(state["dus_history"]) >= 3:
                values = [float(x) for _, x in state["dus_history"][-3:]]

    if len(values) < 3:
        print("DPIR1 trigger: nema dovoljno DUS1 podataka za infer:", values)
        return

    a, b, c = values[-3], values[-2], values[-1]
    eps = 2.0

    descending = (a - b > eps) and (b - c > eps)
    ascending = (b - a > eps) and (c - b > eps)

    with lock:
        if descending:
            state["people_count"] += 1
            direction = "ULAZAK"
        elif ascending:
            state["people_count"] = max(0, state["people_count"] - 1)
            direction = "IZLAZAK"
        else:
            direction = "NEJASNO"

        count = state["people_count"]



# -----------------------------
# Tačka 2 : DPIR1 -> DL1 ON 10s
# -----------------------------
def activate_dl1_for_10s():
    now = time.time()

    with lock:
        state["dl1_on"] = True
        state["dl1_until"] = now + 10.0

    # Posalji komandu ka DL1 aktuatoru
    mqtt_send(TOPIC_DL1_CMD, {"command": "ON"})
    print("[DL1] ON for 10s")


def background_loop():
    """
    Pozadinska petlja:
    - gasi DL1 kad istekne 10s
    """
    while True:
        should_turn_off_dl1 = False

        with lock:
            if state["dl1_on"] and time.time() >= state["dl1_until"]:
                state["dl1_on"] = False
                state["dl1_until"] = 0.0
                should_turn_off_dl1 = True

        if should_turn_off_dl1:
            mqtt_send(TOPIC_DL1_CMD, {"command": "OFF"})
            print("[DL1] OFF (timeout)")

        time.sleep(0.1)


# -----------------------------
# Sensor handling (minimalno)
# -----------------------------
def handle_sensor_message(data):
    name = data.get("name")
    if not name:
        return

    value = data.get("value")
    now = time.time()

    # cuvaj trenutna stanja + DUS1 istoriju
    with lock:
        if name == "DPIR1":
            state["sensors"]["DPIR1"] = value

        elif name == "DUS1":
            try:
                d = float(value)
                state["sensors"]["DUS1"] = d
                state["dus_history"].append((now, d))
                state["dus_history"] = [(t, x) for (t, x) in state["dus_history"] if now - t <= 20]
            except Exception:
                pass

    # kad DPIR1 detektuje pokret
    if name == "DPIR1" and str(value) in ("1", "True", "true", "detected"):
        # tačka 2: uključi DL1 na 10s
        activate_dl1_for_10s()
        # tačka 3: odredi ulazak/izlazak preko DUS1
        infer_entry_exit_from_dus1()


# -----------------------------
# MQTT setup
# -----------------------------
def on_connect(client, userdata, flags, rc):
    print("MQTT CONNECTED:", rc)
    client.subscribe("#")  # za sad sve topice


def on_message(client, userdata, msg):
    print("MQTT:", msg.topic, msg.payload)
    try:
        data = json.loads(msg.payload.decode())
    except Exception as e:
        print("JSON ERROR:", e)
        return

    # upis u bazu
    save_to_db(data)
    # obrada senzora
    handle_sensor_message(data)

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect("127.0.0.1", 1883, 60)
print("Subscribing to ALL topics...")
mqtt_client.loop_start()


# -----------------------------
# routes
# -----------------------------
@app.route("/status", methods=["GET"])
def status():
    with lock:
        return jsonify({
            "people_count": state["people_count"],
            "dl1_on": state["dl1_on"],
            "dl1_until": state["dl1_until"],
            "sensors": state["sensors"],
            "dus_history_last_5": state["dus_history"][-5:]
        })


@app.route("/store_data", methods=["POST"])
def store_data_route():
    """
    Rucni upis (debug)
    """
    try:
        data = request.get_json(force=True)
        save_to_db(data)
        handle_sensor_message(data)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


def handle_influx_query(query):
    try:
        query_api = influxdb_client.query_api()
        tables = query_api.query(query, org=org)

        container = []
        for table in tables:
            for record in table.records:
                container.append(record.values)

        return jsonify({"status": "success", "data": container})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/simple_query", methods=["GET"])
def retrieve_simple_data():
    query = f"""from(bucket: "{bucket}")
    |> range(start: -10m)
    |> filter(fn: (r) => r._measurement == "Humidity")"""
    return handle_influx_query(query)


@app.route("/aggregate_query", methods=["GET"])
def retrieve_aggregate_data():
    query = f"""from(bucket: "{bucket}")
    |> range(start: -10m)
    |> filter(fn: (r) => r._measurement == "Humidity")
    |> mean()"""
    return handle_influx_query(query)



if __name__ == "__main__":
    # start background timeout loop
    threading.Thread(target=background_loop, daemon=True).start()

    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)