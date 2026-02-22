import time

try:
    import RPi.GPIO as GPIO
except Exception:
    GPIO = None


COLOR_MAP = {
    "off":       (0, 0, 0),
    "white":     (1, 1, 1),
    "red":       (1, 0, 0),
    "green":     (0, 1, 0),
    "blue":      (0, 0, 1),
    "yellow":    (1, 1, 0),
    "purple":    (1, 0, 1),
    "lightBlue": (0, 1, 1),
}


class RealBrgbLed:
    """
    Event-driven real BRGB LED:
    - čeka komande (set_color)
    - ne vrti sequence periodično
    """

    def __init__(self, settings: dict, on_change):
        if GPIO is None:
            raise RuntimeError("RPi.GPIO not available. Are you running on Raspberry Pi?")

        self.settings = settings
        self.on_change = on_change
        self.tick = float(settings.get("sim_tick", 0.05))

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        pins = settings.get("pins", [12, 13, 19])
        self.r_pin, self.g_pin, self.b_pin = int(pins[0]), int(pins[1]), int(pins[2])

        for p in (self.r_pin, self.g_pin, self.b_pin):
            GPIO.setup(p, GPIO.OUT)

        self._current = "off"
        self._pending = None

        # inicijalno ugasi
        self._apply_color("off")

    def _apply_color(self, name: str):
        rgb = COLOR_MAP.get(name, COLOR_MAP["off"])
        GPIO.output(self.r_pin, GPIO.HIGH if rgb[0] else GPIO.LOW)
        GPIO.output(self.g_pin, GPIO.HIGH if rgb[1] else GPIO.LOW)
        GPIO.output(self.b_pin, GPIO.HIGH if rgb[2] else GPIO.LOW)

    def set_color(self, color: str):
        self._pending = str(color)

    def run(self, stop_event):
        try:
            # inicijalni state event (opciono)
            self.on_change(self._current)

            while not stop_event.is_set():
                if self._pending is not None:
                    color = self._pending
                    self._pending = None

                    self._apply_color(color)
                    self._current = color
                    self.on_change(color)

                time.sleep(self.tick)

        finally:
            self.cleanup()

    def cleanup(self):
        try:
            self._apply_color("off")
        except Exception:
            pass
        try:
            GPIO.cleanup(self.r_pin)
            GPIO.cleanup(self.g_pin)
            GPIO.cleanup(self.b_pin)
        except Exception:
            pass