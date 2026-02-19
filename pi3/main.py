import threading
from infrastructure.publisher import start_publisher_thread
from pi3.settings import load_settings

from pi3.components.brgb import run_brgb

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
    print("Starting PI3")

    settings = load_settings()
    threads = []
    stop_event = threading.Event()

    start_publisher_thread()

    # Only RGB for now
    run_brgb(settings["BRGB"], threads, stop_event)

    print_help()

    try:
        while True:
            cmd = input("input> ").strip()
            if not cmd:
                continue

            if cmd == "exit":
                break

            elif cmd == "status":
                brgb = settings["BRGB"]
                print(
                    f"BRGB running | simulated={brgb.get('simulated', True)} | "
                    f"period_s={brgb.get('period_s', 1.0)} | pins={brgb.get('pins', [12, 13, 19])}"
                )

            else:
                print("Wrong input")

    except KeyboardInterrupt:
        print("Stopping")

    finally:
        stop_event.set()
        for t in threads:
            t.join(timeout=1)
        print("Safely Stopped")
