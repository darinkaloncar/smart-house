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
                print(f"LED is {'ON' if door_light.is_on() else 'OFF'}")
                print(f"BUZZER is {'ON' if door_buzzer.is_on() else 'OFF'}")
                print(f"DS1 is {'PRESSED' if ds1.is_pressed() else 'RELEASED'}")
                print(f"DPIR1 motion is {'DETECTED' if dpir1.is_motion_detected() else 'NOT DETECTED'}")

            elif parts[0] == "led" and len(parts) >= 2:
                if parts[1] == "on":
                    door_light.on()
                elif parts[1] == "off":
                    door_light.off()
                elif parts[1] == "toggle":
                    door_light.toggle()
                else:
                    print("Wrong input (use: led on|off|toggle)")

            elif parts[0] == "buzzer" and len(parts) >= 2:
                if parts[1] == "on":
                    door_buzzer.on()
                elif parts[1] == "off":
                    door_buzzer.off()
                elif parts[1] == "beep":
                    door_buzzer.beep(2000)
                else:
                    print("Wrong input (use: buzzer on|off|beep)")

            # DS1 ručne komande
            elif parts[0] == "ds" and len(parts) >= 2:
                if parts[1] == "press":
                    ds1.press()

                elif parts[1] == "release":
                    ds1.release()

                elif parts[1] == "read":
                    print(f"DS1 value = {ds1.read()} ({'PRESSED' if ds1.is_pressed() else 'RELEASED'})")

                elif parts[1] == "trigger":
                    duration = 1.0
                    if len(parts) >= 3:
                        try:
                            duration = float(parts[2])
                        except ValueError:
                            print("Invalid duration, using default 1.0s")
                    ds1.trigger(duration)

                else:
                    print("Wrong input (use: ds press|release|trigger [sec]|read)")

            # PIR ručna komanda
            elif parts[0] == "pir" and len(parts) >= 2:
                if parts[1] == "read":
                    print(f"DPIR1 motion value = {dpir1.read()}")

                elif parts[1] == "trigger":
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
            # DMS ručna komanda
            elif parts[0] == "dms" and len(parts) >= 2:
                if parts[1] == "read":
                    print("DMS keys:", dms.keys())
                    print("DMS states:", dms.read_states())

                elif parts[1] == "tap" and len(parts) >= 3:
                    try:
                        idx = int(parts[2])
                        dms.tap(idx)
                    except ValueError:
                        print("Wrong input (use: dms tap <idx>)")

                elif parts[1] == "tapkey" and len(parts) >= 3:
                    try:
                        dms.tap_key(parts[2])
                    except Exception as e:
                        print(f"Error: {e}")

                elif parts[1] == "pin" and len(parts) >= 3:
                    dms.enter_pin(parts[2])

                else:
                    print("Wrong input (use: dms tap <idx> | dms tapkey <char> | dms pin <digits> | dms read)")
            
            # DUS ručna komanda
            elif parts[0] == "dus" and len(parts) >= 2:
                if parts[1] == "read":
                    d = dus1.read()
                    if d is None:
                        print("DUS1 distance = N/A")
                    else:
                        print(f"DUS1 distance = {d:.2f} cm")

                elif parts[1] == "set" and len(parts) >= 3:
                    try:
                        val = float(parts[2])
                        dus1.set_constant_distance(val)
                        print(f"DUS1 constant distance set to {val:.1f} cm (sim only)")
                    except ValueError:
                        print("Wrong input (use: dus set <cm>)")

                elif parts[1] == "enter":
                    steps = 20
                    if len(parts) >= 3:
                        try:
                            steps = int(parts[2])
                        except ValueError:
                            print("Invalid steps, using default 20")
                    dus1.simulate_enter(steps)

                elif parts[1] == "exit":
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
            if hasattr(dpir1, "impl") and hasattr(dpir1.impl, "cleanup"):
                dpir1.impl.cleanup()
        except Exception:
            pass

        for t in threads:
            t.join(timeout=1)

        print("Safely Stopped")