import threading
import time

from publisher import start_publisher_thread
from settings.settings import load_settings

from components.btn import Button
from components.dht3 import run_dht3
from components.gsg import run_gsg
from components.sd4 import run_sd4

from components.ds2 import DoorSensor
from components.dpir2 import DoorPir
from components.dus2 import DoorUltrasonic

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
except Exception:
    pass


def _get_settings_key(settings: dict, *keys: str):
    for k in keys:
        if k in settings:
            return k
    return None


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

    key = _get_settings_key(settings, "SD4", "4SD")
    if key:
        run_sd4(settings[key], threads, stop_event)
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

        for t in threads:
            t.join(timeout=1)

        print("Safely Stopped")