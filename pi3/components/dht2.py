import json
import threading

from simulators.dht import run_dht_simulator
from sensors.dht import run_dht_loop, DHT

from globals import batch, publish_limit, counter_lock, publish_event


def dht_callback(humidity, temperature, settings, code=None, verbose=False):
    base = {
        "simulated": settings["simulated"],
        "runs_on": settings["runs_on"],
        "name": settings["name"],
    }

    payload_h = {
        **base,
        "measurement": "Humidity",
        "value": float(humidity),
    }
    payload_t = {
        **base,
        "measurement": "Temperature",
        "value": float(temperature),
    }

    with counter_lock:
        batch.append(("Humidity", json.dumps(payload_h), 0, True))
        batch.append(("Temperature", json.dumps(payload_t), 0, True))

        if len(batch) >= publish_limit:
            publish_event.set()

    if verbose:
        print("[DHT]", payload_h)
        print("[DHT]", payload_t)


def run_dht(settings, threads, stop_event):
    simulated = settings.get("simulated", True)
    delay = float(settings.get("delay_s", 2.0))

    if simulated:
        th = threading.Thread(
            target=run_dht_simulator,
            args=(delay, lambda h, t: dht_callback(h, t, settings), stop_event),
            daemon=True
        )
    else:
        pin = int(settings["pin"])
        dht = DHT(pin)
        th = threading.Thread(
            target=run_dht_loop,
            args=(dht, delay, lambda h, t, code=None: dht_callback(h, t, settings, code), stop_event),
            daemon=True
        )

    th.start()
    threads.append(th)
    return th
