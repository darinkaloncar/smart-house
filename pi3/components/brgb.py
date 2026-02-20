import json
import threading

from pi3.globals import batch, publish_limit, counter_lock, publish_event
from pi3.simulators.brgb import run_brgb_simulator


def brgb_callback(color, settings):
    global publish_limit

    payload = {
        "measurement": "BRGB",
        "simulated": settings.get("simulated", True),
        "runs_on": settings["runs_on"],
        "name": settings["name"],
        "value": str(color),
    }

    with counter_lock:
        batch.append(("BRGB", json.dumps(payload), 0, True))
        if len(batch) >= publish_limit:
            publish_event.set()



def run_brgb(settings, threads, stop_event):
    simulated = settings.get("simulated", True)

    if simulated:
        th = threading.Thread(
            target=run_brgb_simulator,
            args=(settings, lambda color: brgb_callback(color, settings), stop_event),
            daemon=True
        )
    else:
        from pi3.sensors.brgb import run_brgb_loop
        th = threading.Thread(
            target=run_brgb_loop,
            args=(settings, brgb_callback, stop_event),
            daemon=True
        )

    th.start()
    threads.append(th)
