import json
import time
import threading

from simulation.simulators.dms import run_dms_simulator
from globals import batch, publish_counter, publish_limit, counter_lock, publish_event


def dms_callback(idx, value, settings, verbose=False):
    global publish_counter, publish_limit

    payload = {
        "measurement": "Button",
        "simulated": settings["simulated"],
        "runs_on": settings["runs_on"],
        "name": settings["name"],
        "index": int(idx),
        "value": int(value)
    }

    with counter_lock:
        batch.append(("Button", json.dumps(payload), 0, True))
        publish_counter += 1

        if publish_counter >= publish_limit:
            publish_event.set()


def run_dms(settings, threads, stop_event):
    th = threading.Thread(
        target=run_dms_simulator,
        args=(1.0, lambda i, v: dms_callback(i, v, settings), stop_event, settings["keys"]),
        daemon=True
    )
    th.start()
    threads.append(th)
