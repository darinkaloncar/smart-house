import threading
import time

from publisher import start_publisher_thread
from settings.settings import load_settings

from components.brgb import BrgbLed
from components.ir import IrRemote
from components.lcd import run_lcd

from components.dht1 import run_dht1
from components.dht2 import run_dht2

# Probaj klasu za DPIR3; fallback na run_dpir3 ako još nije refaktorisano
try:
    from components.dpir3 import DoorPir as Pir3Sensor  # class-style (preferred)
except Exception:
    Pir3Sensor = None
    from components.dpir3 import run_dpir3  # fallback

try:
    import RPi.GPIO as GPIO  # type: ignore
    GPIO.setmode(GPIO.BCM)
except Exception:
    pass

import json
import paho.mqtt.client as mqtt


state_lock = threading.Lock()
pi3_state = {
    "dht": {
        "DHT1": {"temperature": None, "humidity": None, "updated_at": None},
        "DHT2": {"temperature": None, "humidity": None, "updated_at": None},
        "DHT3": {"temperature": None, "humidity": None, "updated_at": None},
    }
}


def update_dht_state(data):
    name = str(data.get("name", ""))
    if name not in ["DHT1", "DHT2", "DHT3"]:
        return False

    dht_type = str(data.get("type", "")).lower()
    if dht_type not in ["temperature", "humidity"]:
        return False

    try:
        value = float(data.get("value"))
    except Exception:
        return False

    with state_lock:
        d = pi3_state["dht"][name]
        d[dht_type] = value
        d["updated_at"] = time.time()

    return True

def get_dht_snapshot():
    with state_lock:
        return {
            k: {
                "temperature": v["temperature"],
                "humidity": v["humidity"],
                "updated_at": v["updated_at"],
            }
            for k, v in pi3_state["dht"].items()
        }

def _run_if_present(settings, key, runner, threads, stop_event):
    if key not in settings:
        print(f"[WARN] Missing settings for {key}")
        return None
    return runner(settings[key], threads, stop_event)


def _get_settings_key(settings: dict, *keys: str):
    for k in keys:
        if k in settings:
            return k
    return None

def start_dht_mqtt_listener(stop_event, broker="127.0.0.1", port=1883):
    """
    Listens for DHT updates forwarded by controller and updates local dht PI3 cache.
    
    """
    TOPIC_DHT_UPDATE = "home/actuators/dht/update"

    def on_connect(client, userdata, flags, rc):
        print("DHT UPDATE MQTT CONNECTED:", rc)
        client.subscribe(TOPIC_DHT_UPDATE)

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
        except Exception as e:
            print("DHT UPDATE MQTT JSON ERROR:", e, msg.payload)
            return
        data = payload.get("update") if isinstance(payload, dict) and "update" in payload else payload
        print("DHT UPDATE MQTT RECEIVED:", data)
        if not isinstance(data, dict):
            print("DHT UPDATE MQTT BAD PAYLOAD:", payload)
            return

        ok = update_dht_state(data)
        if ok:
            name = data.get("name")
            snap = get_dht_snapshot().get(str(name), {})
            print(
                f"[DHT CACHE] {name}: "
                f"T={snap.get('temperature')} "
                f"H={snap.get('humidity')}"
            )
        else:
            print("DHT UPDATE MQTT ignored payload:", data)

    def loop():
        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message

        try:
            client.connect(broker, port, 60)
            client.loop_start()

            while not stop_event.is_set():
                time.sleep(0.1)
        except Exception as e:
            print("DHT UPDATE MQTT LOOP ERROR:", e)
        finally:
            try:
                client.loop_stop()
            except Exception:
                pass
            try:
                client.disconnect()
            except Exception:
                pass

    th = threading.Thread(target=loop, daemon=True)
    th.start()
    return th

def print_help():
    print("""
Commands:
  status
  exit

IR:
  ir <BUTTON>             e.g. ir OK | ir LEFT | ir 1
  irseq <DIGITS>          e.g. irseq 1234
  irmany <B1,B2,...>      e.g. irmany 1,2,3,OK

BRGB:
  brgb <COLOR>            e.g. brgb red | brgb blue | brgb off
  brgb off
  brgb list

DPIR3:
  pir read
  pir trigger
  pir trigger <sec>
""")

if __name__ == "__main__":
    print("Starting PI3")

    settings = load_settings()
    threads = []
    stop_event = threading.Event()

    start_publisher_thread()

    th_dht_listener = start_dht_mqtt_listener(stop_event)
    if th_dht_listener:
        threads.append(th_dht_listener)

    # --- DHT sensors (periodic) ---
    _run_if_present(settings, "DHT1", run_dht1, threads, stop_event)
    _run_if_present(settings, "DHT2", run_dht2, threads, stop_event)

    # --- IR (event-based class) ---
    ir = None
    if "IR" in settings:
        try:
            ir = IrRemote(settings["IR"], verbose=True)
            th_ir = ir.start(stop_event)
            if th_ir:
                threads.append(th_ir)
        except Exception as e:
            print(f"[WARN] IR failed to start: {e}")
    else:
        print("[WARN] Missing settings for IR")

    # --- BRGB (event-based class) ---
    brgb = None
    if "BRGB" in settings:
        try:
            brgb = BrgbLed(settings["BRGB"], verbose=True)
            th_brgb = brgb.start(stop_event)
            if th_brgb:
                threads.append(th_brgb)
        except Exception as e:
            print(f"[WARN] BRGB failed to start: {e}")
    else:
        print("[WARN] Missing settings for BRGB")

    # --- LCD ---
    if "LCD" in settings:
        try:
            run_lcd(settings["LCD"], threads, stop_event, dht_snapshot_getter=get_dht_snapshot)
        except Exception as e:
            print(f"[WARN] LCD failed to start: {e}")
    else:
        print("[WARN] Missing settings for LCD")

    # --- DPIR3 (class-style if available, else fallback runner) ---
    dpir3 = None
    dpir3_key = _get_settings_key(settings, "DPIR3")
    if dpir3_key:
        if Pir3Sensor is not None:
            try:
                dpir3 = Pir3Sensor(settings[dpir3_key], verbose=True)
                th_pir = dpir3.start(stop_event)
                if th_pir:
                    threads.append(th_pir)
            except Exception as e:
                print(f"[WARN] DPIR3 class failed to start: {e}")
        else:
            print("[WARN] DPIR3 class not available, using run_dpir3 fallback (no pir console commands)")
            try:
                _run_if_present(settings, "DPIR3", run_dpir3, threads, stop_event)
            except Exception as e:
                print(f"[WARN] DPIR3 fallback failed to start: {e}")
    else:
        print("[WARN] Missing settings for DPIR3")

    print_help()

    try:
        while True:
            cmd = input("input> ").strip()
            if not cmd:
                continue

            parts = cmd.split()
            if not parts:
                continue

            # ---- basic ----
            if parts[0].lower() == "exit":
                break

            if parts[0].lower() == "status":
                for k in ["DHT1", "DHT2", "IR", "BRGB", "LCD", "DPIR3"]:
                    if k in settings:
                        s = settings[k]
                        print(
                            f"{k}: simulated={s.get('simulated', True)} "
                            f"runs_on={s.get('runs_on', 'PI3')} name={s.get('name', k)}"
                        )

                if ir is not None:
                    print(f"IR buttons: {ir.buttons()}")

                if brgb is not None:
                    print(f"BRGB colors: {brgb.colors()}")

                if dpir3 is not None:
                    try:
                        if hasattr(dpir3, "is_motion_detected"):
                            print(f"DPIR3 motion is {'DETECTED' if dpir3.is_motion_detected() else 'NOT DETECTED'}")
                        elif hasattr(dpir3, "read"):
                            print(f"DPIR3 motion value = {dpir3.read()}")
                    except Exception:
                        pass

                continue

            # -------- IR commands --------
            if parts[0].lower() == "ir":
                if ir is None:
                    print("IR is not initialized.")
                    continue

                if len(parts) < 2:
                    print("Usage: ir <BUTTON>")
                    continue

                btn = " ".join(parts[1:]).strip().upper()
                ir.press(btn)
                continue

            if parts[0].lower() == "irseq":
                if ir is None:
                    print("IR is not initialized.")
                    continue

                if len(parts) < 2:
                    print("Usage: irseq <DIGITS>")
                    continue

                seq = "".join(parts[1:]).strip()
                ir.send_code(seq)
                continue

            if parts[0].lower() == "irmany":
                if ir is None:
                    print("IR is not initialized.")
                    continue

                raw = cmd[len("irmany"):].strip()
                if not raw:
                    print("Usage: irmany <B1,B2,...>")
                    continue

                buttons = [x.strip().upper() for x in raw.split(",") if x.strip()]
                ir.press_many(buttons)
                continue

            # -------- BRGB commands --------
            if parts[0].lower() == "brgb":
                if brgb is None:
                    print("BRGB is not initialized.")
                    continue

                if len(parts) == 1:
                    print("Usage: brgb <COLOR> | brgb off | brgb list")
                    continue

                sub = parts[1]

                if sub.lower() == "list":
                    print("Available BRGB colors:", ", ".join(brgb.colors()))
                    continue

                if sub.lower() == "off":
                    brgb.off()
                    continue

                # npr. lightBlue (ostavi case kako je uneto)
                color = " ".join(parts[1:]).strip()
                brgb.set_color(color)
                continue

            # -------- DPIR3 commands (class-style only) --------
            if parts[0].lower() == "pir":
                if dpir3 is None:
                    print("[ERR] DPIR3 not configured as class (or not available)")
                    continue

                if len(parts) < 2:
                    print("Wrong input (use: pir trigger [sec] | pir read)")
                    continue

                if parts[1].lower() == "read":
                    try:
                        if hasattr(dpir3, "read"):
                            print(f"DPIR3 motion value = {dpir3.read()}")
                        elif hasattr(dpir3, "is_motion_detected"):
                            print(f"DPIR3 motion value = {1 if dpir3.is_motion_detected() else 0}")
                        else:
                            print("[ERR] DPIR3 has no read/is_motion_detected method")
                    except Exception as e:
                        print(f"[ERR] DPIR3 read failed: {e}")
                    continue

                if parts[1].lower() == "trigger":
                    duration = 1.0
                    if len(parts) >= 3:
                        try:
                            duration = float(parts[2])
                        except ValueError:
                            print("Invalid duration, using default 1.0s")

                    def pulse():
                        try:
                            if hasattr(dpir3, "trigger_motion"):
                                # ako tvoja klasa već ima ovu metodu
                                dpir3.trigger_motion(duration)
                                return

                            # fallback stil kao PI2:
                            if hasattr(dpir3, "set_motion"):
                                dpir3.set_motion(1)
                                time.sleep(duration)
                                dpir3.set_motion(0)
                                return

                            # ako ima press/release stil (manje verovatno za PIR)
                            if hasattr(dpir3, "press") and hasattr(dpir3, "release"):
                                dpir3.press()
                                time.sleep(duration)
                                dpir3.release()
                                return

                            print("[ERR] DPIR3 does not support trigger/set_motion")
                        except Exception as e:
                            print(f"[ERR] DPIR3 trigger failed: {e}")

                    threading.Thread(target=pulse, daemon=True).start()
                    continue

                print("Wrong input (use: pir trigger [sec] | pir read)")
                continue

            print("Wrong input")

    except KeyboardInterrupt:
        print("Stopping")

    finally:
        stop_event.set()

        # cleanup class devices first
        if ir is not None:
            try:
                ir.cleanup()
            except Exception:
                pass

        if brgb is not None:
            try:
                brgb.cleanup()
            except Exception:
                pass

        if dpir3 is not None:
            try:
                if hasattr(dpir3, "cleanup"):
                    dpir3.cleanup()
                elif hasattr(dpir3, "impl") and hasattr(dpir3.impl, "cleanup"):
                    dpir3.impl.cleanup()
            except Exception:
                pass

        for t in threads:
            t.join(timeout=1)

        print("Safely Stopped")