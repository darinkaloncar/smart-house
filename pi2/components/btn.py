import json
import threading

from simulators.ds import run_button_simulator
from sensors.button import run_button_real
from globals import batch, publish_limit, counter_lock, publish_event


def btn_callback(value, settings, verbose=False):
    global publish_limit

    payload = {
        "measurement": "Button",
        "simulated": settings["simulated"],
        "runs_on": settings["runs_on"],
        "name": settings["name"],
        "value": int(value)
    }

    with counter_lock:
        batch.append(("Button", json.dumps(payload), 0, True))

        if len(batch) >= publish_limit:
            publish_event.set()


def run_btn(settings, threads, stop_event):
    simulated = settings.get("simulated", True)

    if simulated:
        th = threading.Thread(
            target=run_button_simulator,
            args=(1.5, lambda v: btn_callback(v, settings), stop_event),
            daemon=True
        )
    else:
        pin = int(settings.get("pin"))
        pull_up = bool(settings.get("pull_up", True))
        bouncetime_ms = int(settings.get("bouncetime_ms", 120))

        th = threading.Thread(
            target=run_button_real,
            args=(pin, lambda v: btn_callback(v, settings), stop_event, pull_up, bouncetime_ms),
            daemon=True
        )

    th.start()
    threads.append(th)