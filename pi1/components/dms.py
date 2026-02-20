import json
import threading

from simulators.dms import run_dms_simulator
from sensors.dms import run_dms_real
from globals import batch, publish_counter, publish_limit, counter_lock, publish_event


def dms_callback(idx, value, settings, verbose=False):
    global publish_counter, publish_limit

    payload = {
        "measurement": "Button",
        "simulated": settings["simulated"],
        "runs_on": settings["runs_on"],
        "name": settings["name"],
        "value": int(idx)
    }

    with counter_lock:
        batch.append(("Button", json.dumps(payload), 0, True))
        publish_counter += 1

        if publish_counter >= publish_limit:
            publish_event.set()


def run_dms(settings, threads, stop_event):
    simulated = settings.get("simulated", True)

    if simulated:
        th = threading.Thread(
            target=run_dms_simulator,
            args=(1.0, lambda i, v: dms_callback(i, v, settings), stop_event, settings["keys"]),
            daemon=True
        )
    else:
        row_pins = settings.get("row_pins", [25, 8, 7, 1])
        col_pins = settings.get("col_pins", [12, 16, 20, 21])
        period_s = float(settings.get("period_s", 0.05))
        debounce_s = float(settings.get("debounce_s", 0.15))

        th = threading.Thread(
            target=run_dms_real,
            args=(
                period_s,
                lambda i, v: dms_callback(i, v, settings),
                stop_event,
                settings["keys"],
                row_pins,
                col_pins,
                debounce_s
            ),
            daemon=True
        )

    th.start()
    threads.append(th)