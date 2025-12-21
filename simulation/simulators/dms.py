import time, random

def run_door_simulator(delay, callback, stop_event):
    is_closed = True
    while not stop_event.is_set():
        if random.random() < 0.25:
            is_closed = not is_closed
            callback(is_closed)
        time.sleep(delay)