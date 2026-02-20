try:
    import RPi.GPIO as GPIO  # type: ignore
except Exception:
    GPIO = None


class RealLED:

    def __init__(self, settings: dict):
        if GPIO is None:
            raise RuntimeError("RPi.GPIO not available. Are you running on Raspberry Pi?")

        self.pin = int(settings.get("pin"))
        self.active_high = bool(settings.get("active_high", True))
        self._state = False

        GPIO.setwarnings(False)
        try:
            GPIO.setmode(GPIO.BCM)
        except Exception:
            pass

        GPIO.setup(self.pin, GPIO.OUT)

        self.off()

    def _write(self, on: bool):
        level = GPIO.HIGH if (on == self.active_high) else GPIO.LOW
        GPIO.output(self.pin, level)
        self._state = on

    def on(self):
        self._write(True)

    def off(self):
        self._write(False)

    def is_on(self):
        return self._state

    def cleanup(self):
        try:
            self.off()
        finally:
            try:
                GPIO.cleanup(self.pin)
            except Exception:
                pass
