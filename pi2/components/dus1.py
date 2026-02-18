import json
import time
import threading

from simulation.simulators.dus1 import run_ultrasonic_simulator
from simulation.sensors.dus import run_ultrasonic_real
from globals import batch, publish_counter, publish_limit, counter_lock, publish_event


def us_callback(distance, settings, verbose=False):
    global publish_counter, publish_limit

    payload = {
        "measurement": "Distance",
        "simulated": settings["simulated"],
        "runs_on": settings["runs_on"],
        "name": settings["name"],
        "value": float(distance)
    }

    with counter_lock:
        batch.append(("Distance", json.dumps(payload), 0, True))
        publish_counter += 1

        if publish_counter >= publish_limit:
            publish_event.set()


def run_dus1(settings, threads, stop_event):
    simulated = settings.get("simulated", True)

    if simulated:
        th = threading.Thread(
            target=run_ultrasonic_simulator,
            args=(1.0, lambda d: us_callback(d, settings), stop_event),
            daemon=True
        )
    else:
        trig = int(settings.get("trig_pin", 23))
        echo = int(settings.get("echo_pin", 24))
        period = float(settings.get("period_s", 1.0))
        timeout_s = float(settings.get("timeout_s", 0.02))

        th = threading.Thread(
            target=run_ultrasonic_real,
            args=(trig, echo, period, lambda d: us_callback(d, settings), stop_event, timeout_s),
            daemon=True
        )

    th.start()
    threads.append(th)