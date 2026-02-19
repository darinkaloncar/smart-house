import time, random

def run_pir_simulator(delay, callback, stop_event):
    state = 0
    while not stop_event.is_set():
        state = 1 if random.random() < 0.25 else 0
        callback(state)
        time.sleep(delay)
        