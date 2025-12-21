import threading, time

def pir_callback(value, code="DPIR1"):
    ts = time.strftime("%H:%M:%S", time.localtime())
    msg = "MOTION" if value else "NO_MOTION"
    print(f"[{ts}] {code}: {msg} ({value})")

def run_dpir1(settings, threads, stop_event):
    if settings.get("simulated", True):
        from simulators.dpir1 import run_pir_simulator
        args = (2, pir_callback, stop_event)
    else:
        pass

    th = threading.Thread(target=run_pir_simulator, args=args, daemon=True)
    th.start()
    threads.append(th)