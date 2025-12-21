import threading, time

def dms_callback(is_closed, code="DMS"):
    ts = time.strftime("%H:%M:%S", time.localtime())
    state = "CLOSED" if is_closed else "OPEN"
    print(f"[{ts}] {code}: {state}")

def run_dms(settings, threads, stop_event):
    if settings.get("simulated", True):
        from simulators.dms import run_dms_simulator
        args = (1.0, dms_callback, stop_event)
    else:
        pass

    th = threading.Thread(target=run_dms_simulator, args=args, daemon=True)
    th.start()
    threads.append(th)