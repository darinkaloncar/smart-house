import json
import threading
import queue

from globals import batch, publish_limit, counter_lock, publish_event
from simulators.button import run_button_simulator


class Button:
    def __init__(self, settings, verbose=False):
        self.settings = settings
        self.verbose = verbose
        self.simulated = settings.get("simulated", True)

        self._state = 0
        self._thread = None
        self._cmd_q = queue.Queue()

    def _publish(self, value: int):
        global publish_limit

        self._state = 1 if int(value) else 0

        payload = {
            "measurement": "Button",
            "simulated": self.settings.get("simulated", True),
            "runs_on": self.settings.get("runs_on", "PI2"),
            "name": self.settings.get("name", "BTN"),
            "value": int(self._state)
        }

        topic = f"{payload['runs_on']}/{payload['name']}"

        with counter_lock:
            batch.append((topic, json.dumps(payload), 0, True))
            if len(batch) >= publish_limit:
                publish_event.set()

        if self.verbose:
            print(f"[{payload['name']}] BTN={self._state}")

    def press(self):
        if self.simulated:
            self._cmd_q.put("press")
        else:
            pass

    def read(self):
        return int(self._state)

    def start(self, stop_event):
        if self._thread and self._thread.is_alive():
            return self._thread

        if self.simulated:
            self._thread = threading.Thread(
                target=run_button_simulator,
                args=(self._cmd_q, self._publish, stop_event),
                daemon=True
            )
            self._thread.start()
            return self._thread

        # REAL hardware
        from sensors.button import run_button_real

        pin = int(self.settings.get("pin"))
        pull_up = bool(self.settings.get("pull_up", True))
        bouncetime_ms = int(self.settings.get("bouncetime_ms", 120))

        self._thread = threading.Thread(
            target=run_button_real,
            args=(pin, self._publish, stop_event, pull_up, bouncetime_ms),
            daemon=True
        )
        self._thread.start()
        return self._thread