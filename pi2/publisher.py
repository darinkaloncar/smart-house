import json
import threading
import time
from paho.mqtt import publish

from globals import batch, publish_limit, counter_lock, publish_event

HOSTNAME = "localhost"
PORT = 1883

def publisher_task():
    global publish_limit

    while True:
        publish_event.wait()

        with counter_lock:
            local_copy = batch.copy()
            batch.clear()

        if local_copy:
            publish.multiple(local_copy, hostname=HOSTNAME, port=PORT)


        publish_event.clear()


def start_publisher_thread():
    th = threading.Thread(target=publisher_task, daemon=True)
    th.start()
    return th
