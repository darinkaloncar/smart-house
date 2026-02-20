import threading
from publisher import start_publisher_thread
from settings.settings import load_settings

from components.brgb import run_brgb
from components.ir import run_ir
from components.lcd import run_lcd

from components.dht1 import run_dht1
from components.dht2 import run_dht2
from components.dpir3 import run_dpir3

try:
    import RPi.GPIO as GPIO  # type: ignore
    GPIO.setmode(GPIO.BCM)
except Exception:
    pass


def _run_if_present(settings, key, runner, threads, stop_event):
    if key not in settings:
        print(f"[WARN] Missing settings for {key}")
        return
    runner(settings[key], threads, stop_event)


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

    _run_if_present(settings, "DHT1", run_dht1, threads, stop_event)
    _run_if_present(settings, "DHT2", run_dht2, threads, stop_event)

    _run_if_present(settings, "IR", run_ir, threads, stop_event)
    _run_if_present(settings, "BRGB", run_brgb, threads, stop_event)
    _run_if_present(settings, "LCD", run_lcd, threads, stop_event)
    _run_if_present(settings, "DPIR3", run_dpir3, threads, stop_event)

    print_help()

    try:
        while True:
            cmd = input("input> ").strip()
            if not cmd:
                continue

            if cmd == "exit":
                break

            if cmd == "status":
                for k in ["DHT1", "DHT2", "IR", "BRGB", "LCD", "DPIR3"]:
                    if k in settings:
                        s = settings[k]
                        print(
                            f"{k}: simulated={s.get('simulated', True)} "
                            f"runs_on={s.get('runs_on', 'PI3')} name={s.get('name', k)}"
                        )
                continue

            print("Wrong input")

    except KeyboardInterrupt:
        print("Stopping")

    finally:
        stop_event.set()
        for t in threads:
            t.join(timeout=1)
        print("Safely Stopped")
