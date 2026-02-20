import threading
import time
from infrastructure.publisher import start_publisher_thread
from pi2.settings.settings import load_settings

from pi2.components.gsg import run_gsg
from pi2.components.sd4 import run_sd4

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
except:
    pass


def print_help():
    print("""
Commands:
  status
  exit
""")


if __name__ == "__main__":
    print("Starting PI2")

    settings = load_settings()

    threads = []
    stop_event = threading.Event()

    start_publisher_thread()
    run_gsg(settings["GSG"], threads, stop_event)
    run_sd4(settings["SD4"], threads, stop_event)

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
                gsg = settings["GSG"]
                print(f"GSG running | simulated={gsg.get('simulated', True)} | period_s={gsg.get('period_s', 2.0)}")
                sd4 = settings["SD4"]
                print(f"SD4 running | simulated={sd4.get('simulated', True)} | start_seconds={sd4.get('start_seconds', 300)}")

            else:
                print("Wrong input")

    except KeyboardInterrupt:
        print("Stopping")

    finally:
        stop_event.set()

        for t in threads:
            t.join(timeout=1)

        print("Safely Stopped")
