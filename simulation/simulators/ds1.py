import time
import random

def run_button_simulator(delay, callback, stop_event):
    state = 0
    while not stop_event.is_set():
        if random.random() < 0.35:
            state = 1 - state
            callback(state)
        time.sleep(delay)
