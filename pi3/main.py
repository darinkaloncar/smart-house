import threading
from publisher import start_publisher_thread
from settings.settings import load_settings

from components.brgb import run_brgb
from components.ir import run_ir
from components.lcd import run_lcd

try:
    import RPi.GPIO as GPIO # type: ignore
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

    run_brgb(settings["BRGB"], threads, stop_event)
    run_ir(settings["IR"], threads, stop_event)
    run_lcd(settings["LCD"], threads, stop_event)
    
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
