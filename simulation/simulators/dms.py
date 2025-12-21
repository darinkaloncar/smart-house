import time, random

def run_dms_simulator(delay, callback, stop_event,keys=3):
    states = [0]*keys
    while not stop_event.is_set():
        k = random.randrange(keys)
        if random.random() < 0.5:
            states[k] = 1 - states[k]
            callback(k, states[k])
        time.sleep(delay)