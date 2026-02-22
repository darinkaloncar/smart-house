import time
import threading


class SimulationIrRemote:
    """
    - ručni event ide kroz komponentu IrRemote.press(...)
    """

    def __init__(self, settings: dict, on_press):
        self.settings = settings
        self.on_press = on_press
        self.tick = float(settings.get("sim_tick", 0.2))

        self._queue = []
        self._lock = threading.Lock()

    def trigger(self, button_name: str):
        with self._lock:
            self._queue.append(str(button_name))

    def run(self, stop_event):
        while not stop_event.is_set():
            to_send = None
            with self._lock:
                if self._queue:
                    to_send = self._queue.pop(0)

            if to_send is not None:
                self.on_press(to_send)

            time.sleep(self.tick)

    def cleanup(self):
        pass