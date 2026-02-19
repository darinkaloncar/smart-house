import time
import random


def run_ir_simulator(settings, callback, stop_event):
    period_s = float(settings.get("period_s", 1.0))

    button_names = settings.get(
        "button_names",
        ["LEFT", "RIGHT", "UP", "DOWN", "OK", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "*", "#"]
    )

    rng = random.Random()

    while not stop_event.is_set():
        name = rng.choice(button_names)
        callback(name)
        time.sleep(period_s)
