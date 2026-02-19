import time


def run_brgb_simulator(settings, callback, stop_event):
    
    period_s = float(settings.get("period_s", 1.0))
    sequence = settings.get(
        "sequence",
        ["off", "white", "red", "green", "blue", "yellow", "purple", "lightBlue"]
    )

    i = 0
    while not stop_event.is_set():
        color = sequence[i % len(sequence)]
        callback(color)
        i += 1
        time.sleep(period_s)
