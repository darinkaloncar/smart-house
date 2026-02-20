import json
import threading

from globals import batch, publish_limit, counter_lock, publish_event
from simulators.sd4 import run_sd4_simulator

def sd4_callback(text4, settings):
    global publish_limit

    payload = {
        "measurement": "SD4",
        "simulated": settings.get("simulated", True),
        "runs_on": settings["runs_on"],
        "name": settings["name"],
        "value": str(text4),
    }

    topic = f"{settings['runs_on']}/{settings['name']}"
    with counter_lock:
        batch.append((topic, json.dumps(payload), 0, True))
        if len(batch) >= publish_limit:
            publish_event.set()


def run_sd4(settings, threads, stop_event):
    simulated = settings.get("simulated", True)

    if simulated:
        th = threading.Thread(
            target=run_sd4_simulator,
            args=(settings, lambda text4: sd4_callback(text4, settings), stop_event),
            daemon=True
        )
    else:
        from pi2.sensors.sd4 import run_sd4_loop
        th = threading.Thread(
            target=run_sd4_loop,
            args=(settings, sd4_callback, stop_event),
            daemon=True
        )

    th.start()
    threads.append(th)
