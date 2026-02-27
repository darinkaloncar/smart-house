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

TOPIC_DL1_CMD = "home/actuators/dl1/cmd"
TOPIC_DB_CMD  = "home/actuators/db/cmd"
TOPIC_RGB_CMD  = "home/actuators/rgb/cmd"
TOPIC_DHT_UPDATE  = "home/actuators/dht/update"
TOPIC_TIMER_SET_CMD = "home/actuators/timer/set"
TOPIC_TIMER_ADD_CMD = "home/actuators/timer/add"
TOPIC_DMS_INJECT = "home/actuators/dms/inject_pin"
TOPIC_BTN_PRESSED = "home/actuators/btn/pressed"
DS_UNLOCKED_SECONDS = 5.0
ALARM_HOLD_S = 10.0         
GSG_COOLDOWN_S = 2.0        
GSG_ACCEL_DELTA_THR = 0.25   
GSG_GYRO_NORM_THR = 80.0  
EMPTY_GRACE_S = 4.0 

# unosenje pina i aktiviranje sistema
ARM_DELAY_S = 10.0        # nakon ispravnog PIN-a -> arm posle 10s
ENTRY_DELAY_S = 10.0      # kad je armed i DS okine -> imaš 10s da uneseš PIN
PIN_CODE = "2110"
VALID_KEYS = set(["0","1","2","3","4","5","6","7","8","9","*","#","A","B","C","D"])

PIN_LEN = 4

lock = threading.Lock()

state = {
    "people_count": 0,
    "sensors": {
        "DS1": 1,
        "DS2": 1,

        "DPIR1": 0,
        "DUS1": None,
        "DPIR2": 0,
        "DUS2": None,
        "DPIR3": 0,

        "GSG": None,
        "DHT1": {"temp": None, "hum": None},
        "DHT2": {"temp": None, "hum": None},
        "DHT3": {"temp": None, "hum": None},
    },

    "dus_history": {
        "DUS1": [],
        "DUS2": [],
    },

    "alarm_sources": {
        "ds_unlocked": {"active": False, "reason": ""},
        "motion_empty": {"active": False, "reason": ""},
        "gsg_move": {"active": False, "reason": ""},
        "armed_breach": {"active": False, "reason": ""},
    },

    "gsg": {
        "accel": {"x": None, "y": None, "z": None},
        "gyro":  {"x": None, "y": None, "z": None},
        "last_trigger": 0.0,
    },

    "dl1_on": False,
    "dl1_until": 0.0,

    "alarm_on": False,
    "alarm_reason": "",
    "alarm_reasons": [],

    "ds": {
        "DS1": {"value": 1, "since": None, "alarm_latched": False, "opened_ts": 0.0},
        "DS2": {"value": 1, "since": None, "alarm_latched": False, "opened_ts": 0.0},
    },

    "empty_grace_until": 0.0,

    "brgb_color": "off",
    "brgb_on": False,
    "timer_seconds": "00:00",
    "timer_add": 0,

    # arming state
    "system_armed": False,
    "arming_pending": False,
    "arming_until": 0.0,

    # entry delay state
    "entry_pending": False,
    "entry_until": 0.0,
    "entry_reason": "",

    # DMS / PIN state
    "pin_set": False,
    "current_pin": None,
    "pin_code": None,
    "pin_masked": "",
    "dms_pin_buf": "",

    "notifications": [],
}

#pin helper
def _clear_alarm_all_sources():
    for k in state["alarm_sources"].keys():
        state["alarm_sources"][k]["active"] = False
        state["alarm_sources"][k]["reason"] = ""
    for ds_name in ("DS1", "DS2"):
        state["ds"][ds_name]["alarm_latched"] = False

def _disarm_and_silence(reason="PIN OK"):
    state["system_armed"] = False
    state["arming_pending"] = False
    state["arming_until"] = 0.0

    state["entry_pending"] = False
    state["entry_until"] = 0.0
    state["entry_reason"] = ""

    _clear_alarm_all_sources()
    state["alarm_on"] = False
    state["alarm_reason"] = reason
    state["alarm_reasons"] = [reason]

    _reset_pin_state()

    mqtt_send(TOPIC_DB_CMD, {"command": "OFF", "reason": reason})

def _reset_pin_state():
    state["pin_set"] = False
    state["pin_code"] = None
    state["pin_masked"] = ""
    state["dms_pin_buf"] = ""

def _start_arming(now: float):
    state["system_armed"] = False

    state["arming_pending"] = True
    state["arming_until"] = now + float(ARM_DELAY_S)

    state["entry_pending"] = False
    state["entry_until"] = 0.0
    state["entry_reason"] = ""

    state["alarm_sources"]["armed_breach"]["active"] = False
    state["alarm_sources"]["armed_breach"]["reason"] = ""

def handle_dms_key(key: str):
    now = time.time()
    k = str(key).strip().upper()

    with lock:
        if k not in VALID_KEYS:
            return

        if k == "*":
            state["dms_pin_buf"] = ""
            return

        if k == "#":
            if len(state["dms_pin_buf"]) < PIN_LEN:
                return
            pin = state["dms_pin_buf"]
            state["dms_pin_buf"] = ""
        else:
            state["dms_pin_buf"] = (state["dms_pin_buf"] + k)[:8]

            if len(state["dms_pin_buf"]) < PIN_LEN:
                return
            pin = state["dms_pin_buf"]
            state["dms_pin_buf"] = ""

        if not state.get("pin_set", False):
            state["pin_set"] = True
            state["pin_code"] = pin
            state["pin_masked"] = "*" * len(pin)

            _start_arming(now)

            print(f"[PIN] Master PIN set. Arming in {ARM_DELAY_S}s")
            return

        if pin == state.get("pin_code"):
            print("[PIN] Correct PIN -> disarm")
            _disarm_and_silence("PIN OK (disarm)")
            return

        print("[PIN] Wrong PIN")

# alarm helper
def _recompute_alarm(now: float):
    desired = (
        state["alarm_sources"]["ds_unlocked"]["active"]
        or state["alarm_sources"]["motion_empty"]["active"]
        or state["alarm_sources"]["gsg_move"]["active"]
        or state["alarm_sources"]["armed_breach"]["active"]
    )

    reasons = []
    for k in ("ds_unlocked", "motion_empty", "gsg_move", "armed_breach"):
        src = state["alarm_sources"][k]
        if src.get("active"):
            reasons.append(src.get("reason") or k)

    state["alarm_reasons"] = reasons
    state["alarm_reason"] = "; ".join(reasons)

    current = bool(state.get("alarm_on", False))
    if desired == current:
        return

    state["alarm_on"] = desired

    mqtt_send(
        TOPIC_DB_CMD,
        {"command": "ON" if desired else "OFF", "reason": state["alarm_reason"]}
    )
    print(f"[ALARM] {'ON' if desired else 'OFF'} reasons={reasons}")


def alarm_pulse(source_key: str, hold_s: float, reason: str):
    now = time.time()

    with lock:
        state["alarm_sources"][source_key]["active"] = True
        state["alarm_sources"][source_key]["reason"] = reason
        _recompute_alarm(now)

    def _off_later():
        time.sleep(float(hold_s))
        with lock:
            state["alarm_sources"][source_key]["active"] = False
            state["alarm_sources"][source_key]["reason"] = ""
            _recompute_alarm(time.time())

    threading.Thread(target=_off_later, daemon=True).start()

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
    try:
        if "measurement" not in data:
            return

        measurement = str(data["measurement"])
        name = str(data.get("name", ""))

        point = (
            Point(measurement)
            .tag("simulated", str(data.get("simulated", True)))
            .tag("runs_on", str(data.get("runs_on", "")))
            .tag("name", name)
        )

        value = data.get("value", None)

        if measurement == "IR" or name == "IR":
            point = point.field("value_text", "" if value is None else str(value))
        else:
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

def is_empty_but_in_grace(now: float) -> bool:
    return int(state.get("people_count", 0)) == 0 and now < float(state.get("empty_grace_until", 0.0))

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
    values = get_last_dus_values_from_db(dus_name=dus_name, runs_on=runs_on, n=3, lookback_s=15)

    if len(values) < 3:
        with lock:
            hist = state["dus_history"].get(dus_name, [])
            if len(hist) >= 3:
                values = [float(x) for _, x in hist[-3:]]

    if len(values) < 3:
        return (None, False)

    a, b, c = values[-3], values[-2], values[-1]
    eps = 2.0

    descending = (a - b > eps) and (b - c > eps)
    ascending  = (b - a > eps) and (c - b > eps)

    exit_from_zero = False

    with lock:
        before = int(state.get("people_count", 0))

        if descending:
            state["people_count"] = before + 1
            direction = "ULAZAK"

            state["alarm_sources"]["motion_empty"]["active"] = False
            state["alarm_sources"]["motion_empty"]["reason"] = ""

        elif ascending:
            direction = "IZLAZAK"

            if before == 0:
                exit_from_zero = True
            else:
                state["people_count"] = before - 1

            state["alarm_sources"]["motion_empty"]["active"] = False
            state["alarm_sources"]["motion_empty"]["reason"] = ""

            after = int(state.get("people_count", 0))
            if after == 0 and before > 0:
                state["empty_grace_until"] = time.time() + EMPTY_GRACE_S

        else:
            direction = "NEJASNO"

        after = int(state.get("people_count", 0))

    print(f"[{dus_name}] {direction} -> people_count={after} exit_from_zero={exit_from_zero}")
    return (direction, exit_from_zero)

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
        should_turn_off_dl1 = False

        with lock:
            if state.get("arming_pending", False) and now >= float(state.get("arming_until", 0.0)):
                state["arming_pending"] = False
                state["arming_until"] = 0.0
                state["system_armed"] = True
                print("[ARM] System ARMED")

            ds_should_be_on = False
            ds_reason = ""

            for ds_name in ("DS1", "DS2"):
                ds = state["ds"][ds_name]

                # 0 = open
                if ds["value"] == 0 and ds["since"] is not None:
                    if (now - ds["since"]) >= DS_UNLOCKED_SECONDS:
                        ds["alarm_latched"] = True

                if ds["alarm_latched"]:
                    ds_should_be_on = True
                    if not ds_reason:
                        ds_reason = f"{ds_name} open > {DS_UNLOCKED_SECONDS}s"

            state["alarm_sources"]["ds_unlocked"]["active"] = ds_should_be_on
            state["alarm_sources"]["ds_unlocked"]["reason"] = ds_reason

            if state.get("system_armed", False):
                # start entry only on "recent open event"
                if not state.get("entry_pending", False) and not state.get("alarm_on", False):
                    who = ""
                    opened_at = 0.0

                    for ds_name in ("DS1", "DS2"):
                        ts = float(state["ds"][ds_name].get("opened_ts", 0.0))
                        if ts > opened_at:
                            opened_at = ts
                            who = ds_name

                    if opened_at > 0.0 and (now - opened_at) < 1.0:
                        state["entry_pending"] = True
                        state["entry_until"] = now + ENTRY_DELAY_S
                        state["entry_reason"] = f"{who} opened while armed"
                        print(f"[ENTRY] Pending {ENTRY_DELAY_S}s reason={state['entry_reason']}")

                # when entry is done - breach alarm source ON
                if state.get("entry_pending", False) and now >= float(state.get("entry_until", 0.0)):
                    state["alarm_sources"]["armed_breach"]["active"] = True
                    state["alarm_sources"]["armed_breach"]["reason"] = state.get("entry_reason") or "Entry delay expired"
            else:
                # not armed -> clear entry/breach
                state["entry_pending"] = False
                state["entry_until"] = 0.0
                state["entry_reason"] = ""
                state["alarm_sources"]["armed_breach"]["active"] = False
                state["alarm_sources"]["armed_breach"]["reason"] = ""

            if state.get("dl1_on", False) and now >= float(state.get("dl1_until", 0.0)):
                state["dl1_on"] = False
                state["dl1_until"] = 0.0
                should_turn_off_dl1 = True

            _recompute_alarm(now)

        if should_turn_off_dl1:
            mqtt_send(TOPIC_DL1_CMD, {"command": "OFF"})
            print("[DL1] OFF (timeout)")

        time.sleep(0.1)

def _norm_ds01(v) -> int:
    # 0 = open, 1 = closed
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, (int, float)):
        return 1 if int(v) != 0 else 0

    s = str(v).strip().lower()
    if s in ("0", "false", "open", "released"):
        return 0
    if s in ("1", "true", "closed", "pressed"):
        return 1

    # fallback
    try:
        return 1 if int(float(s)) != 0 else 0
    except Exception:
        return 0
    

def trigger_motion_empty_alarm(pir_name: str, why: str):
    with lock:
        state["alarm_sources"]["motion_empty"]["active"] = True
        state["alarm_sources"]["motion_empty"]["reason"] = f"{pir_name}: {why}"
        _recompute_alarm(time.time())

def build_dht_update_payload(data: dict):
    name = str(data.get("name", ""))
    if not name.startswith("DHT"):
        return None

    measurement = str(data.get("measurement", "")).lower()

    if "temperature" in measurement:
        dht_type = "temperature"
    elif "humidity" in measurement:
        dht_type = "humidity"
    else:
        return None

    return {
        "name": name,
        "type": dht_type,      # "temperature" ili "humidity"
        "value": data.get("value")
    }


COLOR_ORDER = [
    "white",     # 1
    "red",       # 2
    "green",     # 3
    "blue",      # 4
    "yellow",    # 5
    "purple",    # 6
    "lightBlue", # 7
]

def ir_value_to_command(value):
    if value is None:
        return None

    v = str(value).strip().lower()

    # numeričke vrednosti
    if v.isdigit():
        n = int(v)

        if n == 0:
            return "off"

        # 1.. -> boje
        idx = n - 1
        if 0 <= idx < len(COLOR_ORDER):
            return COLOR_ORDER[idx]

    return None
    
def handle_sensor_message(data):
    name = data.get("name")
    if not name:
        return

    value = data.get("value")
    now = time.time()

    measurement = data.get("measurement", "")
    if name == "BTN":
        if value == 1:
            mqtt_send(TOPIC_TIMER_ADD_CMD, {"value": state.get("timer_add", 0)})

    if name == "DMS" or str(data.get("measurement", "")).upper() == "DMS":
        handle_dms_key(value)
        return

    if name == "IR":
            print(f"[IR] sensor message received: {value}")

            color = ir_value_to_command(value)
            if color is None:
                print(f"[IR] unsupported value: {value}")
                return

            print(f"[BRGB] command update via sensor message: {color}")
            mqtt_send(TOPIC_RGB_CMD, {"command": color})
            with lock:
                state["brgb_color"] = color
                state["brgb_on"] = (color.lower() != "off")
            return
    if name == "SD4":
        with lock:
            state["timer_seconds"] = value
     # --- DHT ---
    if str(name).startswith("DHT"):
        _update_dht_state(str(name), measurement, value)
        dht_payload = build_dht_update_payload(data)
        if dht_payload is not None:
            mqtt_send(TOPIC_DHT_UPDATE, dht_payload)
        return
    if name == "GSG":
        with lock:
            state["sensors"]["GSG"] = value
        handle_gsg_message(measurement, value)
        return

    if name in ("DS1", "DS2"):
        v01 = _norm_ds01(value)
        with lock:
            ds_state = state["ds"][name]
            prev = ds_state["value"]
            ds_state["value"] = v01
            state["sensors"][name] = v01

            if prev != v01:
                if v01 == 0:
                    ds_state["since"] = now
                    ds_state["opened_ts"] = now
                else:
                    ds_state["since"] = None
                    ds_state["alarm_latched"] = False

        return

    with lock:
        if name in ("DPIR1", "DPIR2", "DPIR3"):
            state["sensors"][name] = value

        elif name in ("DUS1", "DUS2"):
            try:
                d = float(value)
                state["sensors"][name] = d

                hist = state["dus_history"].setdefault(name, [])
                hist.append((now, d))

                # keep last 20s
                state["dus_history"][name] = [(t, x) for (t, x) in hist if now - t <= 20]
            except Exception:
                pass
    

    is_motion = str(value) in ("1", "True", "true", "detected")
    if name not in ("DPIR1", "DPIR2", "DPIR3") or not is_motion:
        return

    if name == "DPIR1":
        activate_dl1_for_10s()

        direction, exit_from_zero = infer_entry_exit_from_dus("DUS1", "PI1")
        with lock:
            pc_after = int(state.get("people_count", 0))
            grace_until = float(state.get("empty_grace_until", 0.0))
            in_grace = (pc_after == 0 and now < grace_until)
            
        if direction == "ULAZAK":
            return

        if exit_from_zero:
            trigger_motion_empty_alarm("DPIR1", "IZLAZAK while people_count=0")
        
        if direction == "IZLAZAK" and pc_after == 0:
            return

        if in_grace:
            print(f"[DPIR1] motion ignored (empty grace until {grace_until:.2f})")
            return

        if pc_after == 0:
            trigger_motion_empty_alarm("DPIR1", f"motion while empty (dus={direction})")

        return

    if name == "DPIR2":
        direction, exit_from_zero = infer_entry_exit_from_dus("DUS2", "PI2")

        with lock:
            pc_after = int(state.get("people_count", 0))
            grace_until = float(state.get("empty_grace_until", 0.0))
            in_grace = (pc_after == 0 and now < grace_until)

        if direction == "ULAZAK":
            return

        if exit_from_zero:
            trigger_motion_empty_alarm("DPIR2", "IZLAZAK while people_count=0")
            return

        if direction == "IZLAZAK" and pc_after == 0:
            return

        if in_grace:
            print(f"[DPIR2] motion ignored (empty grace until {grace_until:.2f})")
            return

        if pc_after == 0:
            trigger_motion_empty_alarm("DPIR2", f"motion while empty (dus={direction})")

        return

    if name == "DPIR3":
        with lock:
            pc = int(state.get("people_count", 0))
            grace_until = float(state.get("empty_grace_until", 0.0))
            in_grace = (pc == 0 and now < grace_until)

        if pc == 0 and not in_grace:
            trigger_motion_empty_alarm("DPIR3", "motion while empty")
        return


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
        if (abs(ax) < 1e-6 and abs(ay) < 1e-6 and abs(az) < 1e-6 and
            abs(gx) < 1e-6 and abs(gy) < 1e-6 and abs(gz) < 1e-6):
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

def _update_dht_state(name: str, measurement: str, value):
    # name: DHT1/DHT2/DHT3
    m = str(measurement or "").lower()

    try:
        v = None if value is None else float(value)
    except Exception:
        v = None

    with lock:
        if name not in state["sensors"] or not isinstance(state["sensors"][name], dict):
            state["sensors"][name] = {"temp": None, "hum": None}

        if "temperature" in m or "temp" in m:
            state["sensors"][name]["temp"] = v
        elif "humidity" in m or "hum" in m:
            state["sensors"][name]["hum"] = v
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
    
    if msg.topic == TOPIC_DB_CMD:
        cmd = str(data.get("command", "")).upper()

        if cmd == "OFF":
            print("[ALARM] Manual OFF received")

            with lock:
                for k in state["alarm_sources"].keys():
                    state["alarm_sources"][k]["active"] = False
                    state["alarm_sources"][k]["reason"] = ""

                for ds_name in ("DS1", "DS2"):
                    state["ds"][ds_name]["alarm_latched"] = False

                state["alarm_on"] = False
                state["alarm_reason"] = "Manual OFF"
                state["alarm_reasons"] = ["Manual OFF"]

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
            "people_count": state.get("people_count", 0),

            "dl1_on": state.get("dl1_on", False),
            "dl1_until": state.get("dl1_until", 0.0),

            "sensors": state.get("sensors", {}),

            "alarm_on": state.get("alarm_on", False),
            "reason": state.get("alarm_reason", ""),
            "alarm_reasons": state.get("alarm_reasons", []),

            "ds_debug": state.get("ds", {}),

            "dus_history_last_5": {
                "DUS1": state.get("dus_history", {}).get("DUS1", [])[-5:],
                "DUS2": state.get("dus_history", {}).get("DUS2", [])[-5:],
            },

            "brgb_color": state.get("brgb_color", "off"),
            "brgb_on": state.get("brgb_on", False),

            "system_armed": state.get("system_armed", False),
            "arming_pending": state.get("arming_pending", False),
            "arming_until": state.get("arming_until", 0.0),

            "entry_pending": state.get("entry_pending", False),
            "entry_until": state.get("entry_until", 0.0),
            "entry_reason": state.get("entry_reason", ""),

            "pin_set": state.get("pin_set", False),
            "pin_masked": state.get("pin_masked", "****" if state.get("pin_set") else ""),

            "notifications": state.get("notifications", []),
            "timer_seconds": state.get("timer_seconds", 0),
            "timer_blink": state.get("timer_blink", False),
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

@app.route("/rgb", methods=["POST"])
def set_rgb_route():
    try:
        data = request.get_json(force=True) or {}
        color = str(data.get("command", "")).strip()

        mqtt_send(TOPIC_RGB_CMD, {"command": color})

        with lock:
            state["brgb_color"] = color
            state["brgb_on"] = (color.lower() != "off")

        return jsonify({"status": "success", "color": color})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route("/dms/key", methods=["POST"])
def dms_key_route():
    data = request.get_json(force=True) or {}
    key = str(data.get("key", "")).strip()
    if not key:
        return jsonify({"status": "error", "message": "missing key"}), 400

    handle_dms_key(key)
    return jsonify({"status": "ok"})
@app.route("/timer/set", methods=["POST"])
def timer_set_route():
    try:
        data = request.get_json(force=True) or {}
        seconds = int(data.get("seconds", 0))

        # MMSS clamp (99:59 max)
        seconds = max(0, min(seconds, 99 * 60 + 59))

        mqtt_send(TOPIC_TIMER_SET_CMD, {"set": seconds})


        return jsonify({
            "status": "success",
            "seconds": seconds,
            "topic": TOPIC_TIMER_SET_CMD,
            "payload": {"set": seconds}
        })
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "Invalid seconds"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route("/timer/add", methods=["POST"])
def timer_add_route():
    try:
        data = request.get_json(force=True) or {}
        seconds = int(data.get("seconds", 0))

        # add može biti i negativan
        seconds = max(-(99 * 60 + 59), min(seconds, 99 * 60 + 59))
        state["timer_add"] = seconds

        return jsonify({
            "status": "success",
            "seconds": seconds,
            "topic": TOPIC_TIMER_ADD_CMD,
            "payload": {"add": seconds}
        })
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "Invalid seconds"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route("/dms/pin", methods=["POST"])
def dms_pin_route():
    data = request.get_json(force=True) or {}
    pin = str(data.get("pin", "")).strip().upper()

    if not pin:
        return jsonify({"status": "error", "message": "missing pin"}), 400
    if len(pin) > 8:
        return jsonify({"status": "error", "message": "pin too long (max 8)"}), 400
    if any(ch not in VALID_KEYS for ch in pin):
        return jsonify({"status": "error", "message": "invalid chars (allowed: 0-9 A-D * #)"}), 400

    mqtt_send(TOPIC_DMS_INJECT, {
        "measurement": "DMS",
        "name": "DMS",
        "value": pin,
        "event": "pin",
        "source": "web",
    })

    return jsonify({"status": "ok"})

@app.route("/btn/pressed", methods=["POST"])
def btn_pressed_route():
    try:
        payload = {"cmd": "pressed"}
        mqtt_send(TOPIC_BTN_PRESSED, payload)

        return jsonify({
            "status": "success",
            "topic": TOPIC_BTN_PRESSED,
            "payload": payload
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == "__main__":
    # start background timeout loop
    threading.Thread(target=background_loop, daemon=True).start()

    app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)