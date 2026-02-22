import time
import threading


class SimulationBrgbLed:
    """
    Event-driven BRGB simulator:
    - boja se menja ručno preko set_color(...)
    """

    def __init__(self, settings: dict, on_change):
        self.settings = settings
        self.on_change = on_change
        self.tick = float(settings.get("sim_tick", 0.2))
        self._current = "off"

        self._queue = []
        self._lock = threading.Lock()

    def set_color(self, color: str):
        with self._lock:
            self._queue.append(str(color))

    def run(self, stop_event):
        # inicijalno stanje
        self.on_change(self._current)

        while not stop_event.is_set():
            next_color = None
            with self._lock:
                if self._queue:
                    next_color = self._queue.pop(0)

            if next_color is not None:
                self._current = next_color
                self.on_change(self._current)

            time.sleep(self.tick)

    def cleanup(self):
        pass