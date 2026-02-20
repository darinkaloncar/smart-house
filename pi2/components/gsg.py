import json
import threading
from simulators.gsg import run_gsg_simulator
from globals import batch, publish_limit, counter_lock, publish_event
from sensors.gsg import run_gsg_loop


def _append_axis_payloads(prefix, values, settings):
    axes = ["X", "Y", "Z"]
    for i, axis in enumerate(axes):
        payload = {
            "measurement": f"{prefix} {axis}",
            "simulated": settings.get("simulated", True),
            "runs_on": settings["runs_on"],
            "name": settings["name"],
            "value": float(values[i]),
        }
        batch.append((f"{prefix} {axis}", json.dumps(payload), 0, True))


def gsg_callback(accel, gyro, settings):

    global publish_limit

    with counter_lock:
        _append_axis_payloads("Accelerometer", accel, settings)
        _append_axis_payloads("Gyroscope", gyro, settings)

        if len(batch) >= publish_limit:
            publish_event.set()


def run_gsg(settings, threads, stop_event):
    simulated = settings.get("simulated", True)
    period_s = float(settings.get("period_s", 2.0))

    if simulated:
        th = threading.Thread(
            target=run_gsg_simulator,
            args=(period_s, lambda a, g: gsg_callback(a, g, settings), stop_event),
            daemon=True
        )
    else:
        th = threading.Thread(
            target=run_gsg_loop,
            args=(period_s, gsg_callback, stop_event, settings),
            daemon=True
        )


    th.start()
    threads.append(th)
