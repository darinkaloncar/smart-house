import json
import time
import threading

from globals import batch, publish_limit, counter_lock, publish_event


class DoorUltrasonic:
    """
    - cuva poslednju izmerenu distancu
    - publishuje MQTT za svako merenje
    """

    def __init__(self, settings, verbose: bool = False):
        self.settings = settings
        self.verbose = verbose
        self.simulated = settings.get("simulated", True)

        self._distance_cm = None
        self._thread = None
        self._lock = threading.Lock()

        if self.simulated:
            from simulators.dus import SimulationUltrasonic
            self.impl = SimulationUltrasonic(settings, on_distance=self._on_distance)
        else:
            from sensors.dus import RealUltrasonic
            self.impl = RealUltrasonic(settings, on_distance=self._on_distance)

    def _publish_distance(self, distance_cm: float):
        global publish_limit

        payload = {
            "measurement": "Distance",
            "simulated": self.settings["simulated"],
            "runs_on": self.settings["runs_on"],
            "name": self.settings["name"],
            "value": round(float(distance_cm), 2)
        }

        topic = f"{self.settings['runs_on']}/{self.settings['name']}"
        with counter_lock:
            batch.append((topic, json.dumps(payload), 0, True))
            if len(batch) >= publish_limit:
                publish_event.set()

    def _on_distance(self, distance_cm: float):
        try:
            d = float(distance_cm)
        except Exception:
            return

        with self._lock:
            self._distance_cm = d

        if self.verbose:
            ts = time.strftime("%H:%M:%S", time.localtime())

        self._publish_distance(d)

    def start(self, stop_event):
        if self._thread and self._thread.is_alive():
            return self._thread

        self._thread = threading.Thread(
            target=self.impl.run,
            args=(stop_event,),
            daemon=True
        )
        self._thread.start()
        return self._thread

    def read(self):
        with self._lock:
            return self._distance_cm

    def set_constant_distance(self, distance_cm: float):
        if hasattr(self.impl, "set_constant_distance"):
            self.impl.set_constant_distance(distance_cm)

    def simulate_enter(self, steps: int = 20):
        if hasattr(self.impl, "simulate_enter"):
            self.impl.simulate_enter(steps)

    def simulate_exit(self, steps: int = 20):
        if hasattr(self.impl, "simulate_exit"):
            self.impl.simulate_exit(steps)

    def cleanup(self):
        try:
            if hasattr(self.impl, "cleanup"):
                self.impl.cleanup()
        except Exception:
            pass