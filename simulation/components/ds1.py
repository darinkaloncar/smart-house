import threading
import time

def ds1_callback(value, code="DS1"):
    ts = time.strftime("%H:%M:%S", time.localtime())
    state = "PRESSED" if value else "RELEASED"
    print(f"[{ts}] {code}: {state} ({value})")

def run_ds1(settings, threads, stop_event):
    if settings.get("simulated", True):
        from simulators.ds1 import run_button_simulator
        args = (1.5, ds1_callback, stop_event)
    else:
        pass

    th = threading.Thread(target=run_button_simulator, args=args, daemon=True)
    th.start()
    threads.append(th)
