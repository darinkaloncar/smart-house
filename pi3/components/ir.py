import json
import threading

from globals import batch, publish_counter, publish_limit, counter_lock, publish_event
from pi3.simulators.ir import run_ir_simulator


def ir_callback(button_name, settings):
    global publish_counter, publish_limit

    payload = {
        "measurement": "IR",
        "simulated": settings.get("simulated", True),
        "runs_on": settings["runs_on"],
        "name": settings["name"],
        "value": str(button_name),
    }

    with counter_lock:
        batch.append(("IR", json.dumps(payload), 0, True))
        publish_counter += 1
        if publish_counter >= publish_limit:
            publish_event.set()


def run_ir(settings, threads, stop_event):
    simulated = settings.get("simulated", True)

    if simulated:
        th = threading.Thread(
            target=run_ir_simulator,
            args=(settings, lambda name: ir_callback(name, settings), stop_event),
            daemon=True
        )
    else:
        from pi3.sensors.ir import run_ir_loop
        th = threading.Thread(
            target=run_ir_loop,
            args=(settings, ir_callback, stop_event),
            daemon=True
        )

    th.start()
    threads.append(th)
