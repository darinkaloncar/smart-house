import threading
from publisher import start_publisher_thread
from settings.settings import load_settings

from components.ds2 import run_ds2
from components.dpir2 import run_dpir2
from components.dus2 import run_dus2
from components.btn import run_btn
from components.dht3 import run_dht3
from components.gsg import run_gsg
from components.sd4 import run_sd4 

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
  status
  exit
""")


if __name__ == "__main__":
    print("Starting PI2")

    settings = load_settings()
    threads = []
    stop_event = threading.Event()

    start_publisher_thread()

    key = _get_settings_key(settings, "DS2")
    if key:
        run_ds2(settings[key], threads, stop_event)
    else:
        print("[WARN] Missing settings for DS2")

    key = _get_settings_key(settings, "DUS2")
    if key:
        run_dus2(settings[key], threads, stop_event)
    else:
        print("[WARN] Missing settings for DUS2")

    key = _get_settings_key(settings, "DPIR2")
    if key:
        run_dpir2(settings[key], threads, stop_event)
    else:
        print("[WARN] Missing settings for DPIR2")

    key = _get_settings_key(settings, "SD4")
    if key:
        run_sd4(settings[key], threads, stop_event)
    else:
        print("[WARN] Missing settings for 4SD/SD4")

    key = _get_settings_key(settings, "BTN")
    if key:
        run_btn(settings[key], threads, stop_event)
    else:
        print("[WARN] Missing settings for BTN")

    key = _get_settings_key(settings, "DHT3")
    if key:
        run_dht3(settings[key], threads, stop_event)
    else:
        print("[WARN] Missing settings for DHT3")

    key = _get_settings_key(settings, "GSG")
    if key:
        run_gsg(settings[key], threads, stop_event)
    else:
        print("[WARN] Missing settings for GSG")

    print_help()

    try:
        while True:
            cmd = input("input> ").strip()
            if not cmd:
                continue

            if cmd == "exit":
                break

            if cmd == "status":
                for device_key in ["DS2", "DUS2", "DPIR2", "BTN", "DHT3", "GSG", "4SD", "SD4"]:
                    if device_key in settings:
                        s = settings[device_key]
                        print(
                            f"{device_key}: simulated={s.get('simulated', True)} "
                            f"runs_on={s.get('runs_on', 'PI2')} name={s.get('name', device_key)}"
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
