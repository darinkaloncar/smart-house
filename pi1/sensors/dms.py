import time

try:
    import RPi.GPIO as GPIO
except Exception:
    GPIO = None


class RealDmsKeypad:
    """
    Šalje on_change(idx, state) za press/release.
    """

    def __init__(self, settings: dict, on_change):
        if GPIO is None:
            raise RuntimeError("RPi.GPIO not available. Are you running on Raspberry Pi?")

        self.on_change = on_change
        self.keys = settings.get("keys")
        self.row_pins = settings.get("row_pins", [25, 8, 7, 1])
        self.col_pins = settings.get("col_pins", [12, 16, 20, 21])
        self.period_s = float(settings.get("period_s", 0.05))
        self.debounce_s = float(settings.get("debounce_s", 0.15))

        self.rows = len(self.row_pins)
        self.cols = len(self.col_pins)

        if self.rows <= 0 or self.cols <= 0:
            raise ValueError("DMS row_pins/col_pins must not be empty")

        GPIO.setwarnings(False)
        try:
            GPIO.setmode(GPIO.BCM)
        except Exception:
            pass

        for rp in self.row_pins:
            GPIO.setup(rp, GPIO.OUT, initial=GPIO.LOW)

        for cp in self.col_pins:
            GPIO.setup(cp, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

        self._prev_state = [[0] * self.cols for _ in range(self.rows)]
        self._last_change_time = {}
    def _idx_of(self, r: int, c: int) -> int:
        return r * self.cols + c

    def run(self, stop_event):
        try:
            while not stop_event.is_set():
                for r, rp in enumerate(self.row_pins):
                    GPIO.output(rp, GPIO.HIGH)
                    time.sleep(0.0005)

                    for c, cp in enumerate(self.col_pins):
                        pressed = 1 if GPIO.input(cp) else 0
                        prev = self._prev_state[r][c]

                        if pressed != prev:
                            now = time.time()
                            key_rc = (r, c)
                            last = self._last_change_time.get(key_rc, 0.0)

                            # debounce na promenu press/release
                            if (now - last) >= self.debounce_s:
                                self._last_change_time[key_rc] = now
                                self._prev_state[r][c] = pressed
                                self.on_change(self._idx_of(r, c), pressed)

                    GPIO.output(rp, GPIO.LOW)

                time.sleep(self.period_s)

        finally:
            self.cleanup()

    def cleanup(self):
        try:
            for rp in self.row_pins:
                GPIO.cleanup(rp)
            for cp in self.col_pins:
                GPIO.cleanup(cp)
        except Exception:
            pass