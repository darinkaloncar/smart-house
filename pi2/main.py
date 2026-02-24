import threading
import time
import json

import paho.mqtt.client as mqtt

from publisher import start_publisher_thread
from settings.settings import load_settings

from components.btn import Button
from components.dht3 import run_dht3
from components.gsg import run_gsg
from components.sd4 import SD4

from components.ds2 import DoorSensor
from components.dpir2 import DoorPir
from components.dus2 import DoorUltrasonic

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
except Exception:
    pass

BROKER_HOST = "127.0.0.1"
BROKER_PORT = 1883
def _get_settings_key(settings: dict, *keys: str):
    for k in keys:
        if k in settings:
            return k
    return None


def start_timer_mqtt_listener(stop_event, sd4, broker=BROKER_HOST, port=BROKER_PORT):
    """
    Sluša timer komande sa kontrolera i poziva SD4 wrapper:
      - topic set: {"set": <seconds>}
      - topic add: {"add": <seconds>}
    """
    TOPIC_TIMER_SET_CMD = "home/actuators/timer/set"
    TOPIC_TIMER_ADD_CMD = "home/actuators/timer/add"

    def on_connect(client, userdata, flags, rc):
        print("TIMER MQTT CONNECTED:", rc)
        client.subscribe(TOPIC_TIMER_SET_CMD)
        client.subscribe(TOPIC_TIMER_ADD_CMD)

    def on_message(client, userdata, msg):
        if sd4 is None:
            print("[TIMER MQTT] SD4 not initialized, ignoring command")
            return

        try:
            payload = json.loads(msg.payload.decode())
        except Exception as e:
            print("TIMER MQTT JSON ERROR:", e, msg.payload)
            return
        try:
            if msg.topic == TOPIC_TIMER_SET_CMD:
                if "set" not in payload:
                    print("TIMER MQTT BAD SET PAYLOAD:", payload)
                    return

                seconds = int(payload.get("set", 0))
                seconds = max(0, min(seconds, 99 * 60 + 59))

                sd4.set_seconds(seconds)
                print(f"[TIMER MQTT] SET -> {seconds}s")

            elif msg.topic == TOPIC_TIMER_ADD_CMD:
                if "add" not in payload:
                    print("TIMER MQTT BAD ADD PAYLOAD:", payload)
                    return

                seconds = int(payload.get("add", 0))
                seconds = max(-(99 * 60 + 59), min(seconds, 99 * 60 + 59))                

                sd4.add_seconds(seconds)
                sign = "+" if seconds >= 0 else ""
                print(f"[TIMER MQTT] ADD -> {sign}{seconds}s")

        except Exception as e:
            print("TIMER MQTT HANDLE ERROR:", e, "payload=", payload)

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
            print("TIMER MQTT LOOP ERROR:", e)

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
  ds press
  ds release
  ds trigger
  ds trigger <sec>
  ds read

  pir trigger
  pir trigger <sec>
  pir read

  dus read
  dus set <cm>
  dus enter
  dus enter <steps>
  dus exit
  dus exit <steps>

  btn press

  gsg move <intensity>

  sd4 start
  sd4 set <sec>
  sd4 add <sec>
  sd4 read

  status
  exit
""")


if __name__ == "__main__":
    print("Starting PI2")

    settings = load_settings()
    threads = []
    stop_event = threading.Event()

    start_publisher_thread()

    ds2 = None
    key = _get_settings_key(settings, "DS2")
    if key:
        ds2 = DoorSensor(settings[key], verbose=True)
        t = ds2.start(stop_event)
        if t:
            threads.append(t)
    else:
        print("[WARN] Missing settings for DS2")

    dus2 = None
    key = _get_settings_key(settings, "DUS2")
    if key:
        dus2 = DoorUltrasonic(settings[key], verbose=True)
        t = dus2.start(stop_event)
        if t:
            threads.append(t)
    else:
        print("[WARN] Missing settings for DUS2")

    dpir2 = None
    key = _get_settings_key(settings, "DPIR2")
    if key:
        dpir2 = DoorPir(settings[key], verbose=True)
        t = dpir2.start(stop_event)
        if t:
            threads.append(t)
    else:
        print("[WARN] Missing settings for DPIR2")

    sd4 = None
    key = _get_settings_key(settings, "SD4", "4SD")
    if key:
        sd4 = SD4(settings[key], verbose=True)

        th_timer_listener = start_timer_mqtt_listener(stop_event, sd4)
        if th_timer_listener:
            threads.append(th_timer_listener)

    else:
        print("[WARN] Missing settings for 4SD/SD4")

    key = _get_settings_key(settings, "DHT3")
    if key:
        run_dht3(settings[key], threads, stop_event)
    else:
        print("[WARN] Missing settings for DHT3")

    gsg_cmd_q = None
    key = _get_settings_key(settings, "GSG")
    if key:
        gsg_cmd_q = run_gsg(settings[key], threads, stop_event)
    else:
        print("[WARN] Missing settings for GSG")

    btn = None
    key = _get_settings_key(settings, "BTN")
    if key:
        btn = Button(settings[key], verbose=True)
        t = btn.start(stop_event)
        if t:
            threads.append(t)
    else:
        print("[WARN] Missing settings for BTN")

    print_help()

    try:
        while True:
            cmd = input("input> ").strip()
            if not cmd:
                continue

            parts = cmd.split()

            if parts[0] == "exit":
                break

            elif parts[0] == "status":
                # config info
                for device_key in ["DS2", "DUS2", "DPIR2", "BTN", "DHT3", "GSG", "4SD", "SD4"]:
                    if device_key in settings:
                        s = settings[device_key]
                        print(
                            f"{device_key}: simulated={s.get('simulated', True)} "
                            f"runs_on={s.get('runs_on', 'PI2')} name={s.get('name', device_key)}"
                        )

                # runtime
                if ds2:
                    print(f"DS2 is {'PRESSED' if ds2.is_pressed() else 'RELEASED'}")
                if dpir2:
                    print(f"DPIR2 motion is {'DETECTED' if dpir2.is_motion_detected() else 'NOT DETECTED'}")
                if dus2:
                    d = dus2.read()
                    print(f"DUS2 distance = {d:.2f} cm" if d is not None else "DUS2 distance = N/A")
                if sd4:
                    try:
                        print(f"SD4 display = {sd4.read()} ({sd4.read_seconds()}s)")
                    except Exception:
                        print("SD4 display = N/A")

            elif parts[0] == "gsg" and len(parts) >= 2:
                if not gsg_cmd_q:
                    print("[ERR] GSG not in simulated mode (or not configured)")
                    continue

                if parts[1] == "move":
                    intensity = 1.0
                    if len(parts) >= 3:
                        try:
                            intensity = float(parts[2])
                        except ValueError:
                            print("Invalid intensity, using 1.0")
                    gsg_cmd_q.put(("move", intensity))
                    print(f"GSG simulated move (intensity={intensity})")

                elif parts[1] == "set" and len(parts) == 8:
                    # gsg set ax ay az gx gy gz
                    try:
                        ax, ay, az, gx, gy, gz = map(float, parts[2:])
                        gsg_cmd_q.put(("set", ax, ay, az, gx, gy, gz))
                        print("GSG set -> one publish sent")
                    except ValueError:
                        print("Wrong input (numbers expected)")

                else:
                    print("Wrong input (use: gsg move [intensity] | gsg set ax ay az gx gy gz)")

            elif parts[0] == "ds" and len(parts) >= 2:
                if not ds2:
                    print("[ERR] DS2 not configured")
                    continue

                if parts[1] == "press":
                    ds2.press()

                elif parts[1] == "release":
                    ds2.release()

                elif parts[1] == "read":
                    print(f"DS2 value = {ds2.read()} ({'PRESSED' if ds2.is_pressed() else 'RELEASED'})")

                elif parts[1] == "trigger":
                    duration = 1.0
                    if len(parts) >= 3:
                        try:
                            duration = float(parts[2])
                        except ValueError:
                            print("Invalid duration, using default 1.0s")
                    ds2.trigger(duration)

                else:
                    print("Wrong input (use: ds press|release|trigger [sec]|read)")

            elif parts[0] == "pir" and len(parts) >= 2:
                if not dpir2:
                    print("[ERR] DPIR2 not configured")
                    continue

                if parts[1] == "read":
                    print(f"DPIR2 motion value = {dpir2.read()}")

                elif parts[1] == "trigger":
                    duration = 1.0
                    if len(parts) >= 3:
                        try:
                            duration = float(parts[2])
                        except ValueError:
                            print("Invalid duration, using default 1.0s")

                    def pulse():
                        dpir2.set_motion(1)
                        time.sleep(duration)
                        dpir2.set_motion(0)

                    threading.Thread(target=pulse, daemon=True).start()

                else:
                    print("Wrong input (use: pir trigger [sec]|read)")

            elif parts[0] == "btn" and len(parts) >= 2:
                if not btn:
                    print("[ERR] BTN not configured")
                    continue

                if parts[1] == "press":
                    btn.press()
                else:
                    print("Wrong input (use: btn press)")

            elif parts[0] == "dus" and len(parts) >= 2:
                if not dus2:
                    print("[ERR] DUS2 not configured")
                    continue

                if parts[1] == "read":
                    d = dus2.read()
                    if d is None:
                        print("DUS2 distance = N/A")
                    else:
                        print(f"DUS2 distance = {d:.2f} cm")

                elif parts[1] == "set" and len(parts) >= 3:
                    try:
                        val = float(parts[2])
                        dus2.set_constant_distance(val)
                        print(f"DUS2 constant distance set to {val:.1f} cm (sim only)")
                    except ValueError:
                        print("Wrong input (use: dus set <cm>)")

                elif parts[1] == "enter":
                    steps = 20
                    if len(parts) >= 3:
                        try:
                            steps = int(parts[2])
                        except ValueError:
                            print("Invalid steps, using default 20")
                    dus2.simulate_enter(steps)

                elif parts[1] == "exit":
                    steps = 20
                    if len(parts) >= 3:
                        try:
                            steps = int(parts[2])
                        except ValueError:
                            print("Invalid steps, using default 20")
                    dus2.simulate_exit(steps)

                else:
                    print("Wrong input (use: dus read | dus set <cm> | dus enter [steps] | dus exit [steps])")

            # ---------------- SD4  ----------------
            elif parts[0] == "sd4" and len(parts) >= 2:
                if not sd4:
                    print("[ERR] SD4/4SD not configured")
                    continue

                if parts[1] == "start":
                    sd4.start()
                    print("SD4 countdown started")

                elif parts[1] == "set" and len(parts) >= 3:
                    try:
                        sec = int(parts[2])
                        sd4.set_seconds(sec)
                        print(f"SD4 set to {sec}s")
                    except ValueError:
                        print("Wrong input (use: sd4 set <sec>)")

                elif parts[1] == "add" and len(parts) >= 3:
                    try:
                        sec = int(parts[2])
                        sd4.add_seconds(sec)
                        sign = "+" if sec >= 0 else ""
                        print(f"SD4 add {sign}{sec}s")
                    except ValueError:
                        print("Wrong input (use: sd4 add <sec>)")

                elif parts[1] == "read":
                    print(f"SD4 display = {sd4.read()} ({sd4.read_seconds()}s)")

                else:
                    print("Wrong input (use: sd4 start | sd4 set <sec> | sd4 add <sec> | sd4 read)")

            else:
                print("Wrong input")

    except KeyboardInterrupt:
        print("Stopping")

    finally:
        stop_event.set()

        try:
            if ds2:
                ds2.cleanup()
        except Exception:
            pass

        try:
            if dus2:
                dus2.cleanup()
        except Exception:
            pass

        try:
            if dpir2 and hasattr(dpir2, "impl") and hasattr(dpir2.impl, "cleanup"):
                dpir2.impl.cleanup()
        except Exception:
            pass

        try:
            if sd4:
                sd4.shutdown()
        except Exception:
            pass

        for t in threads:
            t.join(timeout=1)

        print("Safely Stopped")