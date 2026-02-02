import json
import time
import threading

from simulation.simulators.dpir1 import run_pir_simulator
from globals import batch, publish_counter, publish_limit, counter_lock, publish_event


def pir_callback(value, settings, verbose=False):
    global publish_counter, publish_limit

    if verbose:
        ts = time.strftime("%H:%M:%S", time.localtime())
        print(f"[DPIR1] MOTION={value}")

    payload = {
        "measurement": "Motion",
        "simulated": settings["simulated"],
        "runs_on": settings["runs_on"],
        "name": settings["name"],
        "value": int(value)
    }

    with counter_lock:
        batch.append(("Motion", json.dumps(payload), 0, True))
        publish_counter += 1

        if publish_counter >= publish_limit:
            publish_event.set()


def run_dpir1(settings, threads, stop_event):
    th = threading.Thread(
        target=run_pir_simulator,
        args=(2, lambda v: pir_callback(v, settings), stop_event),
        daemon=True
    )
    th.start()
    threads.append(th)
