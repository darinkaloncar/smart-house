import json
import time
import threading

from globals import batch, publish_limit, counter_lock, publish_event


class SD4:
    """
    4-digit 7-segment.

    API:
      - start()
      - set_seconds(seconds)
      - add_seconds(seconds)
      - shutdown()

    """

    def __init__(self, settings, verbose: bool = False):
        self.settings = settings
        self.verbose = verbose
        self.simulated = settings.get("simulated", True)

        self._lock = threading.Lock()
        self._text4 = "00:00"
        self._remaining = int(settings.get("start_seconds", 300))
        self._started = False

        if self.simulated:
            from simulators.sd4 import SD4Simulator
            self.impl = SD4Simulator(settings, callback=self._on_display_update)
        else:
            from pi2.sensors.sd4 import SD4Timer
            self.impl = SD4Timer(settings, callback=self._on_display_update)


    def _publish_state(self):
        global publish_limit

        with self._lock:
            text4 = str(self._text4)

        payload = {
            "measurement": "SD4",
            "simulated": self.settings.get("simulated", True),
            "runs_on": self.settings["runs_on"],
            "name": self.settings["name"],
            "value": text4,
        }

        topic = f"{self.settings['runs_on']}/{self.settings['name']}"

        with counter_lock:
            batch.append((topic, json.dumps(payload), 0, True))
            if len(batch) >= publish_limit:
                publish_event.set()

    def _on_display_update(self, text4, settings=None):
        """
        Callback iz impl.
        """
        text4 = str(text4)

        # parsiranje MMSS -> remaining 
        remaining = None
        if len(text4) == 4 and text4.isdigit():
            mm = int(text4[:2])
            ss = int(text4[2:])
            remaining = mm * 60 + ss

        changed = False
        with self._lock:
            if text4 != self._text4:
                self._text4 = text4
                changed = True
            if remaining is not None:
                self._remaining = remaining

        if self.verbose and changed:
            ts = time.strftime("%H:%M:%S", time.localtime())
            print(f"[{self.settings['name']}] {ts} DISPLAY={text4}")

        # publishuj na promenu prikaza (ne na svaki refresh simulatora)
        if changed:
            self._publish_state()


    def start(self):
        """
        Pokreće countdown
        """
        self.impl.start()
        with self._lock:
            self._started = True

    def set_seconds(self, seconds: int):
        self.impl.set_seconds(int(seconds))

    def add_seconds(self, seconds: int):
        self.impl.add_seconds(int(seconds))

    def read(self) -> str:
        with self._lock:
            return str(self._text4)

    def read_seconds(self) -> int:
        with self._lock:
            return int(self._remaining)

    def shutdown(self):
        try:
            self.impl.shutdown()
        except Exception:
            pass