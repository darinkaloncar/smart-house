import threading
from paho.mqtt import publish

from globals import (
    batch_slow,
    batch_fast,
    publish_event_slow,
    publish_event_fast,
    counter_lock
)

HOSTNAME = "localhost"
PORT = 1883

def _drain_loop(batch_ref, event_ref):
    while True:
        event_ref.wait()

        while True:
            with counter_lock:
                if not batch_ref:
                    event_ref.clear()
                    break

                local_copy = batch_ref.copy()
                batch_ref.clear()

            publish.multiple(local_copy, hostname=HOSTNAME, port=PORT)


def start_publisher_threads():
    threading.Thread(target=_drain_loop, args=(batch_fast, publish_event_fast), daemon=True).start()
    threading.Thread(target=_drain_loop,args=(batch_slow, publish_event_slow),daemon=True).start()
