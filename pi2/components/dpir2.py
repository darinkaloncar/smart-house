import json
import time
import threading

from simulators.dpir import run_pir_simulator
from sensors.dpir import run_pir_real
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
    pin = int(settings.get("pin", 4))
    simulated = settings.get("simulated", True)
    target = run_pir_simulator if simulated else run_pir_real

    if simulated:
        args = (2, lambda v: pir_callback(v, settings), stop_event)
    else:
        args = (pin, lambda v: pir_callback(v, settings), stop_event)

    th = threading.Thread(target=target, args=args, daemon=True)
    th.start()
    threads.append(th)
