import threading, time

def us_callback(distance_cm, code="DUS1"):
    ts = time.strftime("%H:%M:%S", time.localtime())
    print(f"[{ts}] {code}: distance={distance_cm:.1f} cm")

def run_dus1(settings, threads, stop_event):
    if settings.get("simulated", True):
        from simulators.dus1 import run_ultrasonic_simulator
        args = (1.0, us_callback, stop_event)
    else:
        pass

    th = threading.Thread(target=run_ultrasonic_simulator, args=args, daemon=True)
    th.start()
    threads.append(th)
