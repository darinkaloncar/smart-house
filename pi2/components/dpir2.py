import json
import time
import threading
from globals import batch, publish_limit, counter_lock, publish_event


class DoorPir:
    def __init__(self, settings, verbose: bool = False):
        self.settings = settings
        self.verbose = verbose
        self.simulated = settings.get("simulated", True)

        self._state = 0
        self._last_change_ts = None
        self._thread = None

        if not self.simulated:
            from sensors.dpir import RealPir
            self.impl = RealPir(settings, on_change=self._on_motion_change)
        else:
            from simulators.dpir import SimulationPir
            self.impl = SimulationPir(settings, on_change=self._on_motion_change)

    def _publish_state(self):
        global publish_limit

        payload = {
            "measurement": "Motion",
            "simulated": self.settings["simulated"],
            "runs_on": self.settings["runs_on"],
            "name": self.settings["name"],
            "value": int(self._state)

        }

        topic = f"{self.settings['runs_on']}/{self.settings['name']}"

        with counter_lock:
            batch.append((topic, json.dumps(payload), 0, True))
            if len(batch) >= publish_limit:
                publish_event.set()

    def _on_motion_change(self, value: int):
        value = 1 if value else 0

        if value == self._state:
            return

        self._state = value
        self._last_change_ts = time.time()

        if self.verbose:
            ts = time.strftime("%H:%M:%S", time.localtime())
            print(f"[{self.settings['name']}] {ts} MOTION={self._state}")

        self._publish_state()

    def start(self, stop_event):
        
        if self._thread and self._thread.is_alive():
            return

        self._thread = threading.Thread(
            target=self.impl.run,
            args=(stop_event,),
            daemon=True
        )
        self._thread.start()
        return self._thread

    def is_motion_detected(self) -> bool:
        return bool(self._state)

    def read(self) -> int:
        return int(self._state)

    def set_motion(self, value: int):
        self._on_motion_change(value)