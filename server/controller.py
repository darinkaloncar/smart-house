from flask import Flask, jsonify, request
from flask_cors import CORS
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import paho.mqtt.client as mqtt
import json
import threading
import time
import math

app = Flask(__name__)
CORS(
    app,
    resources={r"/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}},
    supports_credentials=False
)


# -----------------------------
# InfluxDB Configuration
# -----------------------------
token = "WqfH2n5wWYy1ReLHf-1KVU4pTt_WpBGhE6SMt1rsFVCwC63SOQbzNS-NepTQFhSUmJTiILUQtbX0aT4CcD5q6g=="
org = "MyOrg"
url = "http://localhost:8086"
bucket = "iot"

influxdb_client = InfluxDBClient(url=url, token=token, org=org)

# -----------------------------
# MQTT topics (komande aktuatorima)
# -----------------------------
TOPIC_DL1_CMD = "home/actuators/dl1/cmd"
TOPIC_DB_CMD  = "home/actuators/db/cmd"
DS_UNLOCKED_SECONDS = 5.0
ALARM_HOLD_S = 10.0         
GSG_COOLDOWN_S = 2.0        
GSG_ACCEL_DELTA_THR = 0.25   
GSG_GYRO_NORM_THR = 80.0  


lock = threading.Lock()

state = {
    "people_count": 0,
    "sensors": {
        "DPIR1": 0,
        "DUS1": None,
        "DPIR2": 0,
        "DUS2": None,
        "DPIR3": 0,
        "GSG": None,
    },
    "dus_history": {
        "DUS1": [],
        "DUS2": [],
    },
    "alarm_sources": {
        "ds_unlocked": {"active": False, "reason": ""},
        "motion_empty": {"active": False, "reason": ""},
        "gsg_move": {"active": False, "reason": ""},
    },

    "gsg": {
        "accel": {"x": None, "y": None, "z": None},
        "gyro":  {"x": None, "y": None, "z": None},
        "last_trigger": 0.0,
    },

    "dl1_on": False,
    "dl1_until": 0.0,

    "alarm_on": False,
    "ds": {
        "DS1": {"value": 0, "since": None, "alarm_latched": False},
        "DS2": {"value": 0, "since": None, "alarm_latched": False},
    },
}


# alarm helper
def _recompute_alarm(now: float):
    desired = (
        state["alarm_sources"]["ds_unlocked"]["active"]
        or state["alarm_sources"]["motion_empty"]["active"]
        or state["alarm_sources"]["gsg_move"]["active"]
    )

    current = bool(state.get("alarm_on", False))
    if desired == current:
        return

    state["alarm_on"] = desired

    reasons = []
    for k in ("ds_unlocked", "motion_empty", "gsg_move"):
        if state["alarm_sources"][k]["active"]:
            reasons.append(state["alarm_sources"][k].get("reason", k))

    mqtt_send(TOPIC_DB_CMD, {"command": "ON" if desired else "OFF", "reason": "; ".join(reasons)})
    print(f"[ALARM] {'ON' if desired else 'OFF'} reasons={reasons}")


def alarm_pulse(source_key: str, hold_s: float, reason: str):
    now = time.time()
    with lock:
        state["alarm_sources"]["gsg_move"]["active"] = True
        state["alarm_sources"]["gsg_move"]["reason"] = "GSG significant movement"
        _recompute_alarm(time.time())

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

def get_last_dus_values_from_db(dus_name: str, runs_on: str, n=3, lookback_s=15):
    try:
        query_api = influxdb_client.query_api()
        flux = f'''
from(bucket: "{bucket}")
  |> range(start: -{int(lookback_s)}s)
  |> filter(fn: (r) => r._measurement == "Distance")
  |> filter(fn: (r) => r.name == "{dus_name}")
  |> filter(fn: (r) => r.runs_on == "{runs_on}")
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


def infer_entry_exit_from_dus(dus_name: str, runs_on: str):
    """
    enter = distance opada
    exit  = distance raste
    """
    values = get_last_dus_values_from_db(dus_name=dus_name, runs_on=runs_on, n=3, lookback_s=15)

    # fallback na memoriju ako nema dovoljno u bazi
    if len(values) < 3:
        with lock:
            hist = state["dus_history"].get(dus_name, [])
            if len(hist) >= 3:
                values = [float(x) for _, x in hist[-3:]]

    if len(values) < 3:
        print(f"{dus_name} infer: nema dovoljno podataka:", values)
        return None

    a, b, c = values[-3], values[-2], values[-1]
    eps = 2.0

    descending = (a - b > eps) and (b - c > eps)
    ascending  = (b - a > eps) and (c - b > eps)

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

    print(f"[{dus_name}] {direction} -> people_count={count} (values={values})")
    return direction


def activate_dl1_for_10s():
    now = time.time()

    with lock:
        state["dl1_on"] = True
        state["dl1_until"] = now + 10.0

    mqtt_send(TOPIC_DL1_CMD, {"command": "ON"})
    print("[DL1] ON for 10s")


def background_loop():
    while True:
        now = time.time()

        with lock:
            ds_should_be_on = False
            ds_reason = ""

            for ds_name in ("DS1", "DS2"):
                ds = state["ds"][ds_name]

                # ds["value"] == 1 eq ACTIVE
                if ds["value"] == 1 and ds["since"] is not None:
                    if (now - ds["since"]) >= DS_UNLOCKED_SECONDS:
                        ds["alarm_latched"] = True

                if ds["alarm_latched"]:
                    ds_should_be_on = True
                    if not ds_reason:
                        ds_reason = f"{ds_name} active > {DS_UNLOCKED_SECONDS}s"

            state["alarm_sources"]["ds_unlocked"]["active"] = ds_should_be_on
            state["alarm_sources"]["ds_unlocked"]["reason"] = ds_reason

            should_turn_off_dl1 = False
            if state["dl1_on"] and now >= state["dl1_until"]:
                state["dl1_on"] = False
                state["dl1_until"] = 0.0
                should_turn_off_dl1 = True

            _recompute_alarm(now)

        if should_turn_off_dl1:
            mqtt_send(TOPIC_DL1_CMD, {"command": "OFF"})
            print("[DL1] OFF (timeout)")

        time.sleep(0.1)

def _is_active_signal(v) -> bool:
    if isinstance(v, bool):
        return not v  # ako ti je False = aktivno

    if isinstance(v, (int, float)):
        return int(v) == 0   # 0 is active (for door sensors)

    s = str(v).strip().lower()
    return s in ("0", "false", "open", "released")

def handle_sensor_message(data):
    name = data.get("name")
    if not name:
        return

    value = data.get("value")
    now = time.time()

    measurement = data.get("measurement", "")
    if name == "GSG":
        with lock:
            state["sensors"]["GSG"] = value
        handle_gsg_message(measurement, value)
        return

    if name in ("DS1", "DS2"):
        active = _is_active_signal(value)
        v01 = 1 if active else 0

        with lock:
            ds_state = state["ds"][name]
            prev = ds_state["value"]
            ds_state["value"] = v01
            state["sensors"][name] = v01    

            if prev != v01:
                if v01 == 1:
                    ds_state["since"] = now          # start timer
                else:
                    ds_state["since"] = None         # reset timer
                    ds_state["alarm_latched"] = False

                print(f"[{name}] value={value!r} active={active} v01={v01}")

        return

    # update state and history
    with lock:
        if name in ("DPIR1", "DPIR2", "DPIR3"):
            state["sensors"][name] = value

        elif name in ("DUS1", "DUS2"):
            try:
                d = float(value)
                state["sensors"][name] = d

                hist = state["dus_history"].setdefault(name, [])
                hist.append((now, d))
                # last 20s
                state["dus_history"][name] = [(t, x) for (t, x) in hist if now - t <= 20]
            except Exception:
                pass

    # pir detecting motion
    is_motion = str(value) in ("1", "True", "true", "detected")
    if name in ("DPIR1", "DPIR2", "DPIR3") and is_motion:
        with lock:
            empty = int(state.get("people_count", 0)) == 0
            if empty:
                state["alarm_sources"]["motion_empty"]["active"] = True
                state["alarm_sources"]["motion_empty"]["reason"] = f"{name} motion while people_count=0"
                _recompute_alarm(time.time())

    if name == "DPIR1" and is_motion:
        activate_dl1_for_10s()
        infer_entry_exit_from_dus("DUS1", "PI1")

    if name == "DPIR2" and is_motion:
        infer_entry_exit_from_dus("DUS2", "PI2")

def handle_gsg_message(measurement: str, value):
    try:
        v = float(value)
    except Exception:
        return

    m = str(measurement or "")
    ml = m.strip().lower()

    is_acc = "accelerometer" in ml or "accel" in ml
    is_gyr = "gyroscope" in ml or "gyro" in ml
    if not (is_acc or is_gyr):
        return

    axis = None
    if ml.endswith(" x"):
        axis = "x"
    elif ml.endswith(" y"):
        axis = "y"
    elif ml.endswith(" z"):
        axis = "z"
    if axis is None:
        return

    now = time.time()

    moved = False
    acc_norm = None
    gyr_norm = None

    with lock:
        g = state["gsg"]

        if is_acc:
            g["accel"][axis] = v
        else:
            g["gyro"][axis] = v

        ax, ay, az = g["accel"]["x"], g["accel"]["y"], g["accel"]["z"]
        gx, gy, gz = g["gyro"]["x"],  g["gyro"]["y"],  g["gyro"]["z"]

        if ax is None or ay is None or az is None or gx is None or gy is None or gz is None:
            return

        if (now - float(g.get("last_trigger", 0.0))) < GSG_COOLDOWN_S:
            return

        acc_norm = math.sqrt(ax*ax + ay*ay + az*az)
        gyr_norm = math.sqrt(gx*gx + gy*gy + gz*gz)

        moved = (abs(acc_norm - 1.0) >= GSG_ACCEL_DELTA_THR) or (gyr_norm >= GSG_GYRO_NORM_THR)
        if moved:
            g["last_trigger"] = now

    if moved:
        alarm_pulse("gsg_move", ALARM_HOLD_S, reason=f"GSG moved (acc={acc_norm:.2f}, gyro={gyr_norm:.1f})")

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

    save_to_db(data)
    handle_sensor_message(data)

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect("127.0.0.1", 1883, 60)
print("Subscribing to ALL topics...")
mqtt_client.loop_start()


@app.route("/status", methods=["GET"])
def status():
    with lock:
        return jsonify({
            "people_count": state["people_count"],
            "dl1_on": state["dl1_on"],
            "dl1_until": state["dl1_until"],
            "sensors": state["sensors"],

            "alarm_on": state.get("alarm_on", False),
            "ds_debug": state.get("ds", {}),

            "dus_history_last_5": {
                "DUS1": state.get("dus_history", {}).get("DUS1", [])[-5:],
                "DUS2": state.get("dus_history", {}).get("DUS2", [])[-5:],
            },
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

    app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)