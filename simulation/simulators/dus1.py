import time, random

def run_ultrasonic_simulator(delay, callback, stop_event):
    while not stop_event.is_set():
        dist = random.uniform(10, 150)
        callback(dist)
        time.sleep(delay)
