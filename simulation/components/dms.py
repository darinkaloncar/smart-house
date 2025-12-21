import threading, time

def dms_callback(index, value, code="DMS"):
    ts = time.strftime("%H:%M:%S", time.localtime())
    state = "PRESSED" if value else "RELEASED"
    print(f"[{ts}] {code}[{index}]: {state}")

def run_dms(settings, threads, stop_event):
    if settings.get("simulated", True):
        from simulators.dms import run_dms_simulator
        keys = settings.get("keys", 3)
        args = (1.0, dms_callback, stop_event, keys)
    else:
        pass

    th = threading.Thread(target=run_dms_simulator, args=args, daemon=True)
    th.start()
    threads.append(th)