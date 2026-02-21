import time
import queue

def run_button_simulator(cmd_q: "queue.Queue", callback, stop_event):
    while not stop_event.is_set():
        try:
            cmd = cmd_q.get(timeout=0.1)
        except queue.Empty:
            continue

        if cmd == "press":
            callback(1)
            time.sleep(0.15)
            callback(0)