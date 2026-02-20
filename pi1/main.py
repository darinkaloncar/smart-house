import threading
from publisher import start_publisher_thread

from settings.settings import load_settings

from components.ds1 import run_ds1
from components.dpir1 import run_dpir1
from components.dus1 import run_dus1
from components.dms import run_dms

from components.dl import DoorLight
from components.db import DoorBuzzer

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
except:
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

  status
  exit
""")


if __name__ == "__main__":
    print("Starting")

    settings = load_settings()
    threads = []
    stop_event = threading.Event()
    start_publisher_thread()


    run_ds1(settings["DS1"], threads, stop_event)
    run_dpir1(settings["DPIR1"], threads, stop_event)
    run_dus1(settings["DUS1"], threads, stop_event)
    run_dms(settings["DMS"], threads, stop_event)

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
                if door_light.is_on():
                    print("LED is ON")
                else:
                    print("LED is OFF")
                if door_buzzer.is_on():
                    print("BUZZER is ON")
                else:
                    print("BUZZER is OFF")

            elif parts[0] == "led" and len(parts) >= 2:
                if parts[1] == "on":
                    door_light.on()
                elif parts[1] == "off":
                    door_light.off()
                elif parts[1] == "toggle":
                    door_light.toggle()
                else:
                    print("Wrong input")

            elif parts[0] == "buzzer" and len(parts) >= 2:
                if parts[1] == "on":
                    door_buzzer.on()
                elif parts[1] == "off":
                    door_buzzer.off()
                elif parts[1] == "beep":
                    door_buzzer.beep(2000)
                else:
                    print("Wrong input")

            else:
                print("Wrong input")

    except KeyboardInterrupt:
        print("Stopping")

    finally:
        # Signal to all threads to stop
        stop_event.set()

        door_light.off()
        door_buzzer.off()

        for t in threads:
            t.join(timeout=1)

        print("Safely Stopped")
