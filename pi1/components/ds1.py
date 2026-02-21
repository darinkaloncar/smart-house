import json
import time
import threading

from globals import batch, publish_limit, counter_lock, publish_event


class DoorSensor:
    """
    - drži trenutno stanje (_state): 0=release, 1=pressed/active
    - publishuje MQTT samo na promenu stanja
    - omogućava ručni press/release/trigger iz konzole
    """

    def __init__(self, settings, verbose: bool = False):
        self.settings = settings
        self.verbose = verbose
        self.simulated = settings.get("simulated", True)

        self._state = 0
        self._thread = None
        self._lock = threading.Lock()

        if self.simulated:
            from simulators.ds import SimulationDoorSensor
            self.impl = SimulationDoorSensor(settings, on_change=self._on_state_change)
        else:
            from sensors.button import RealDoorSensor
            self.impl = RealDoorSensor(settings, on_change=self._on_state_change)

    def _publish_state(self):
        global publish_limit

        payload = {
            "measurement": "Button",
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

    def _on_state_change(self, value: int):
        value = 1 if value else 0

        with self._lock:
            if value == self._state:
                return  # publish samo na promenu
            self._state = value

        if self.verbose:
            ts = time.strftime("%H:%M:%S", time.localtime())
            label = "PRESSED" if self._state else "RELEASED"
            print(f"[{self.settings['name']}] {ts} {label} (value={self._state})")

        self._publish_state()

    def start(self, stop_event):
        """
        Pokreće backend petlju (real polling ili sim idle thread).
        """
        if self._thread and self._thread.is_alive():
            return self._thread

        self._thread = threading.Thread(
            target=self.impl.run,
            args=(stop_event,),
            daemon=True
        )
        self._thread.start()
        return self._thread

    def press(self):
        self._on_state_change(1)

    def release(self):
        self._on_state_change(0)

    def trigger(self, duration: float = 1.0):
        """
        Kratak pulse: press -> sleep -> release
        Bez blokiranja pozivaoca (pokreće posebnu nit).
        """
        def _pulse():
            self.press()
            time.sleep(max(0.0, float(duration)))
            self.release()

        threading.Thread(target=_pulse, daemon=True).start()

    def read(self) -> int:
        with self._lock:
            return int(self._state)

    def is_pressed(self) -> bool:
        return bool(self.read())

    def cleanup(self):
        try:
            if hasattr(self.impl, "cleanup"):
                self.impl.cleanup()
        except Exception:
            pass


