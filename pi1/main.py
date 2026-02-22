import threading
import time

from publisher import start_publisher_thread
from settings.settings import load_settings
from components.dms import DmsKeypad
from components.ds1 import DoorSensor
from components.dpir1 import DoorPir
from components.dus1 import DoorUltrasonic
from components.dl import DoorLight
from components.db import DoorBuzzer

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
except Exception:
    pass
import json
import paho.mqtt.client as mqtt

def start_local_dpir1_to_dl_thread(dpir1, door_light, stop_event, on_seconds=10.0, cooldown_s=0.5):
    def loop():
        last_on_until = 0.0
        was_motion = False

        while not stop_event.is_set():
            motion = dpir1.is_motion_detected()
            now = time.time()

            if motion and not was_motion:
                door_light.on()
                last_on_until = now + float(on_seconds)

            # auto-off
            if last_on_until > 0 and now >= last_on_until:
                door_light.off()
                last_on_until = 0.0

            was_motion = motion
            time.sleep(float(cooldown_s))

    th = threading.Thread(target=loop, daemon=True)
    th.start()
    return th

def start_buzzer_mqtt_listener(door_buzzer, stop_event, broker="127.0.0.1", port=1883):
    TOPIC_DB_CMD = "home/actuators/db/cmd"

    def on_connect(client, userdata, flags, rc):
        print("BUZZER MQTT CONNECTED:", rc)
        client.subscribe(TOPIC_DB_CMD)

    def on_message(client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
        except Exception as e:
            print("BUZZER MQTT JSON ERROR:", e, msg.payload)
            return

        cmd = str(data.get("command", "")).upper()

        if cmd == "ON":
            door_buzzer.on()
        elif cmd == "OFF":
            door_buzzer.off()
        elif cmd == "BEEP":
            ms = int(data.get("ms", 2000))
            door_buzzer.beep(ms)
        else:
            print("BUZZER MQTT: unknown command:", data)

    def loop():
        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect(broker, port, 60)
        client.loop_start()

        try:
            while not stop_event.is_set():
                time.sleep(0.1)
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
  led on
  led off
  led toggle

  buzzer on
  buzzer off
  buzzer beep

  ds press
  ds release
  ds trigger
  ds trigger <sec>
  ds read

  pir trigger
  pir trigger <sec>
  pir read

  dms tap <idx>
  dms tapkey <char>
  dms pin <digits>
  dms read

  dus read
  dus set <cm>
  dus enter
  dus enter <steps>
  dus exit
  dus exit <steps>

  status
  help
  exit
""")


if __name__ == "__main__":
    print("Starting")

    settings = load_settings()
    threads = []
    stop_event = threading.Event()

    start_publisher_thread()

    ds1 = DoorSensor(settings["DS1"], verbose=True)
    ds1_thread = ds1.start(stop_event)
    if ds1_thread:
        threads.append(ds1_thread)

    dus1 = DoorUltrasonic(settings["DUS1"], verbose=True)
    dus1_thread = dus1.start(stop_event)
    if dus1_thread:
        threads.append(dus1_thread)
    dms = DmsKeypad(settings["DMS"], verbose=True)
    dms_thread = dms.start(stop_event)
    if dms_thread:
        threads.append(dms_thread)

    dpir1 = DoorPir(settings["DPIR1"], verbose=True)
    dpir_thread = dpir1.start(stop_event)
    if dpir_thread:
        threads.append(dpir_thread)

    # Actuators
    door_light = DoorLight(settings["DL"])
    door_buzzer = DoorBuzzer(settings["DB"])
    buzzer_mqtt_thread = start_buzzer_mqtt_listener(door_buzzer, stop_event)
    threads.append(buzzer_mqtt_thread)

    local_dl_thread = start_local_dpir1_to_dl_thread(dpir1, door_light, stop_event, on_seconds=10.0)
    threads.append(local_dl_thread)

    print_help()

    try:
        while True:
            cmd = input("input> ").strip()
            if not cmd:
                continue

            parts = cmd.split()
            root = parts[0].lower()

            if root == "exit":
                break

            elif root == "help":
                print_help()

            elif root == "status":
                print(f"LED is {'ON' if door_light.is_on() else 'OFF'}")
                print(f"BUZZER is {'ON' if door_buzzer.is_on() else 'OFF'}")
                print(f"DS1 is {'PRESSED' if ds1.is_pressed() else 'RELEASED'}")
                print(f"DPIR1 motion is {'DETECTED' if dpir1.is_motion_detected() else 'NOT DETECTED'}")
                print(f"DMS keys available: {dms.keys()}")  # event-only DMS (nema states)

            elif root == "led" and len(parts) >= 2:
                action = parts[1].lower()
                if action == "on":
                    door_light.on()
                elif action == "off":
                    door_light.off()
                elif action == "toggle":
                    door_light.toggle()
                else:
                    print("Wrong input (use: led on|off|toggle)")

            elif root == "buzzer" and len(parts) >= 2:
                action = parts[1].lower()
                if action == "on":
                    door_buzzer.on()
                elif action == "off":
                    door_buzzer.off()
                    client = mqtt.Client()
                    client.connect("127.0.0.1", 1883, 60)
                    client.publish("home/actuators/db/cmd", json.dumps({"command": "OFF", "reason": "Manual OFF"}))
                    client.disconnect()
                elif action == "beep":
                    door_buzzer.beep(2000)
                else:
                    print("Wrong input (use: buzzer on|off|beep)")

            # DS1 manual commands
            elif root == "ds" and len(parts) >= 2:
                action = parts[1].lower()

                if action == "press":
                    ds1.press()

                elif action == "release":
                    ds1.release()

                elif action == "read":
                    print(f"DS1 value = {ds1.read()} ({'PRESSED' if ds1.is_pressed() else 'RELEASED'})")

                elif action == "trigger":
                    duration = 1.0
                    if len(parts) >= 3:
                        try:
                            duration = float(parts[2])
                        except ValueError:
                            print("Invalid duration, using default 1.0s")
                    ds1.trigger(duration)

                else:
                    print("Wrong input (use: ds press|release|trigger [sec]|read)")

            # PIR manual commands
            elif root == "pir" and len(parts) >= 2:
                action = parts[1].lower()

                if action == "read":
                    print(f"DPIR1 motion value = {dpir1.read()}")

                elif action == "trigger":
                    duration = 1.0
                    if len(parts) >= 3:
                        try:
                            duration = float(parts[2])
                        except ValueError:
                            print("Invalid duration, using default 1.0s")

                    def pulse():
                        dpir1.set_motion(1)
                        time.sleep(duration)
                        dpir1.set_motion(0)

                    th = threading.Thread(target=pulse, daemon=True)
                    th.start()

                else:
                    print("Wrong input (use: pir trigger [sec]|read)")

            # DMS manual commands (EVENT-ONLY: samo pressed publish)
            elif root == "dms" and len(parts) >= 2:
                action = parts[1].lower()

                if action == "read":
                    print("DMS mode: event-only (publishes only PRESSED events)")
                    print("DMS keys:", dms.keys())

                elif action == "tap" and len(parts) >= 3:
                    try:
                        idx = int(parts[2])
                        dms.tap(idx)
                    except ValueError:
                        print("Wrong input (use: dms tap <idx>)")
                    except Exception as e:
                        print(f"Error: {e}")

                elif action == "tapkey" and len(parts) >= 3:
                    try:
                        dms.tap_key(parts[2])
                    except Exception as e:
                        print(f"Error: {e}")

                elif action == "pin" and len(parts) >= 3:
                    dms.enter_pin(parts[2])

                else:
                    print("Wrong input (use: dms tap <idx> | dms tapkey <char> | dms pin <digits> | dms read)")

            # DUS manual commands
            elif root == "dus" and len(parts) >= 2:
                action = parts[1].lower()

                if action == "read":
                    d = dus1.read()
                    if d is None:
                        print("DUS1 distance = N/A")
                    else:
                        print(f"DUS1 distance = {d:.2f} cm")

                elif action == "set" and len(parts) >= 3:
                    try:
                        val = float(parts[2])
                        dus1.set_constant_distance(val)
                        print(f"DUS1 constant distance set to {val:.1f} cm (sim only)")
                    except ValueError:
                        print("Wrong input (use: dus set <cm>)")

                elif action == "enter":
                    steps = 20
                    if len(parts) >= 3:
                        try:
                            steps = int(parts[2])
                        except ValueError:
                            print("Invalid steps, using default 20")
                    dus1.simulate_enter(steps)

                elif action == "exit":
                    steps = 20
                    if len(parts) >= 3:
                        try:
                            steps = int(parts[2])
                        except ValueError:
                            print("Invalid steps, using default 20")
                    dus1.simulate_exit(steps)

                else:
                    print("Wrong input (use: dus read | dus set <cm> | dus enter [steps] | dus exit [steps])")
            else:
                print("Wrong input")

    except KeyboardInterrupt:
        print("Stopping")

    finally:
        stop_event.set()

        try:
            door_light.off()
        except Exception:
            pass

        try:
            door_buzzer.off()
        except Exception:
            pass

        try:
            ds1.cleanup()
        except Exception:
            pass

        try:
            dms.cleanup()
        except Exception:
            pass

        try:
            dus1.cleanup()
        except Exception:
            pass

        try:
            if hasattr(dpir1, "cleanup"):
                dpir1.cleanup()
            elif hasattr(dpir1, "impl") and hasattr(dpir1.impl, "cleanup"):
                dpir1.impl.cleanup()
        except Exception:
            pass

        for t in threads:
            t.join(timeout=1)

        print("Safely Stopped")