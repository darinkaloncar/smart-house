import json
import time
import threading

from simulation.simulators.ds1 import run_button_simulator
from globals import batch, publish_counter, publish_limit, counter_lock, publish_event


def ds1_callback(value, settings, verbose=False):
    global publish_counter, publish_limit

    payload = {
        "measurement": "Button",
        "simulated": settings["simulated"],
        "runs_on": settings["runs_on"],
        "name": settings["name"],
        "value": int(value)
    }

    with counter_lock:
        batch.append(("Button", json.dumps(payload), 0, True))
        publish_counter += 1

        if publish_counter >= publish_limit:
            publish_event.set()


def run_ds1(settings, threads, stop_event):
    th = threading.Thread(
        target=run_button_simulator,
        args=(1.5, lambda v: ds1_callback(v, settings), stop_event),
        daemon=True
    )
    th.start()
    threads.append(th)