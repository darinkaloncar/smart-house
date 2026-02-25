import json
import time
import threading

from globals import batch_fast, counter_lock, publish_event_fast


class SD4:
    """
    4-digit 7-segment wrapper.

    API:
      - start()
      - set_seconds(seconds)
      - add_seconds(seconds)
      - shutdown()

    + blinking support:
      - is_blinking()
      - set_blinking(bool)
    """

    def __init__(self, settings, verbose: bool = False):
        self.settings = settings
        self.verbose = verbose
        self.simulated = settings.get("simulated", True)

        self._lock = threading.Lock()
        self._text4 = "00:00"
        self._remaining = int(settings.get("start_seconds", 300))
        self._started = False
        self._blinking = False

        if self.simulated:
            from simulators.sd4 import SD4Simulator
            self.impl = SD4Simulator(settings, callback=self._on_display_update)
        else:
            from pi2.sensors.sd4 import SD4Timer
            self.impl = SD4Timer(settings, callback=self._on_display_update)

    def _publish_state(self):

        with self._lock:
            text4 = str(self._text4)
            remaining = int(self._remaining)
            blinking = bool(self._blinking)

        payload = {
            "measurement": "SD4",
            "simulated": self.settings.get("simulated", True),
            "runs_on": self.settings["runs_on"],
            "name": self.settings["name"],
            "value": text4,
            "seconds": remaining,
            "blinking": blinking,
        }

        topic = f"{self.settings['runs_on']}/{self.settings['name']}"

        with counter_lock:
            batch_fast.append((topic, json.dumps(payload), 0, False))
            publish_event_fast.set()

    def _parse_text_to_seconds(self, text4: str):
        """
        Podržava i 'MM:SS' i 'MMSS'.
        Vraća int seconds ili None ako ne može da parsira (npr. blank tokom blink-a).
        """
        s = str(text4).strip()

        # tokom blink-a može biti prazno / blank
        if not s:
            return None

        if ":" in s:
            parts = s.split(":")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                mm = int(parts[0])
                ss = int(parts[1])
                return mm * 60 + ss
            return None

        if len(s) == 4 and s.isdigit():
            mm = int(s[:2])
            ss = int(s[2:])
            return mm * 60 + ss

        return None

    def _detect_blinking_from_impl(self):
        """
        Pokušaj da pročita blinking stanje iz impl objekta.
        Ako impl nema blinking atribut/metodu, zadrži postojeće stanje wrapper-a.
        """
        try:
            if hasattr(self.impl, "is_blinking"):
                return bool(self.impl.is_blinking())
            if hasattr(self.impl, "blinking"):
                return bool(getattr(self.impl, "blinking"))
        except Exception:
            pass
        return None

    def _on_display_update(self, text4, settings=None):
        """
        Callback iz impl.
        """
        text4 = str(text4)
        remaining = self._parse_text_to_seconds(text4)
        impl_blinking = self._detect_blinking_from_impl()

        changed = False

        with self._lock:
            if text4 != self._text4:
                self._text4 = text4
                changed = True

            if remaining is not None and remaining != self._remaining:
                self._remaining = remaining
                changed = True

            if impl_blinking is not None and impl_blinking != self._blinking:
                self._blinking = impl_blinking
                changed = True

            current_text = self._text4
            current_blink = self._blinking

        if self.verbose and changed:
            ts = time.strftime("%H:%M:%S", time.localtime())
            blink_txt = " BLINK" if current_blink else ""
            print(f"[{self.settings['name']}] {ts} DISPLAY={current_text}{blink_txt}")

        # publishuj samo kad se nešto stvarno promeni
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
        """
        Set vremena po pravilu gasi blink (ako je bio aktivan).
        """
        sec = int(seconds)

        # prvo ugasi blink
        try:
            if hasattr(self.impl, "set_blinking"):
                self.impl.set_blinking(False)
            elif hasattr(self.impl, "blinking"):
                setattr(self.impl, "blinking", False)
        except Exception:
            pass

        with self._lock:
            if self._blinking:
                self._blinking = False

        self.impl.set_seconds(sec)

    def add_seconds(self, seconds: int):
        """
        Dodavanje sekundi. Sama blink logika (da li da doda ili samo ugasi blink)
        rešava se spolja kroz handle_btn_pressed().
        """
        self.impl.add_seconds(int(seconds))

    def is_blinking(self) -> bool:
        with self._lock:
            return bool(self._blinking)

    def set_blinking(self, value: bool):
        """
        Ručno postavljanje blinking stanja (npr. BTN press da ugasi blink).
        """
        v = bool(value)

        try:
            if hasattr(self.impl, "set_blinking"):
                self.impl.set_blinking(v)
            elif hasattr(self.impl, "blinking"):
                setattr(self.impl, "blinking", v)
        except Exception:
            pass

        changed = False
        with self._lock:
            if self._blinking != v:
                self._blinking = v
                changed = True

        if changed:
            if self.verbose:
                ts = time.strftime("%H:%M:%S", time.localtime())
                print(f"[{self.settings['name']}] {ts} BLINK={'ON' if v else 'OFF'}")
            self._publish_state()

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