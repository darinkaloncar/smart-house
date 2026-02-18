import time


def run_sd4_simulator(settings, callback, stop_event):
    
    start_seconds = int(settings.get("start_seconds", 300))
    period_s = float(settings.get("period_s", 1.0))

    remaining = start_seconds
    last_tick = time.time()

    while not stop_event.is_set():
        now = time.time()
        if now - last_tick >= 1.0:
            if remaining > 0:
                remaining -= 1
            last_tick = now

        mm = remaining // 60
        ss = remaining % 60
        text4 = f"{mm:02d}{ss:02d}"

        callback(text4)
        time.sleep(period_s)
