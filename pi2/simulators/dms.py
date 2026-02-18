import time
import random

def _keys_count(keys):
    if isinstance(keys, int):
        return keys
    if isinstance(keys, (list, tuple)):
        if len(keys) == 0:
            return 0
        # 2D layout
        if isinstance(keys[0], (list, tuple)):
            return sum(len(row) for row in keys)
        # flat list
        return len(keys)
    raise TypeError(f"Unsupported keys type: {type(keys)}")

def run_dms_simulator(delay, callback, stop_event, keys):
    n = _keys_count(keys)
    if n <= 0:
        raise ValueError("DMS simulator: keys count must be > 0")

    states = [0] * n

    while not stop_event.is_set():
        if random.random() < 0.25:
            k = random.randrange(n)
            states[k] = 1
            callback(k, 1)
            time.sleep(0.05)
            states[k] = 0
            callback(k, 0)

        time.sleep(delay)
