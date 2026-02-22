import json
import time
import threading

from globals import batch, publish_limit, counter_lock, publish_event


class BrgbLed:
    """
    Event-driven BRGB LED:
    - publishuje MQTT kada se boja promeni
    - podržava ručno setovanje boje iz konzole
    """

    def __init__(self, settings, verbose: bool = False):
        self.settings = settings
        self.verbose = verbose
        self.simulated = settings.get("simulated", True)

        self._thread = None
        self._last_color = None

        self.allowed_colors = settings.get(
            "sequence",
            ["off", "white", "red", "green", "blue", "yellow", "purple", "lightBlue"]
        )

        if self.simulated:
            from simulators.brgb import SimulationBrgbLed
            self.impl = SimulationBrgbLed(settings, on_change=self._on_color_change)
        else:
            from sensors.brgb import RealBrgbLed
            self.impl = RealBrgbLed(settings, on_change=self._on_color_change)

    def _publish_color_changed(self, color: str):
        global publish_limit

        payload = {
            "measurement": "BRGB",
            "simulated": self.settings.get("simulated", True),
            "runs_on": self.settings["runs_on"],
            "name": self.settings["name"],
            "value": str(color),
            "event": "changed"
        }

        topic = f"{self.settings['runs_on']}/{self.settings['name']}"
        with counter_lock:
            batch.append((topic, json.dumps(payload), 0, True))
            if len(batch) >= publish_limit:
                publish_event.set()

    def _on_color_change(self, color: str):
        color = str(color)

        if color == self._last_color:
            return

        self._last_color = color

        if self.verbose:
            ts = time.strftime("%H:%M:%S", time.localtime())
            print(f"[{self.settings['name']}] {ts} color={color} CHANGED")

        self._publish_color_changed(color)

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

    def cleanup(self):
        try:
            if hasattr(self.impl, "cleanup"):
                self.impl.cleanup()
        except Exception:
            pass

    def set_color(self, color: str):
        color = str(color)

        if hasattr(self.impl, "set_color"):
            self.impl.set_color(color)
        else:
            self._on_color_change(color)

    def off(self):
        self.set_color("off")

    def colors(self):
        return list(self.allowed_colors)

