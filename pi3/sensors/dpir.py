import time

try:
    import RPi.GPIO as GPIO
except Exception:
    GPIO = None


class RealPir:
    def __init__(self, settings: dict, on_change):
        if GPIO is None:
            raise RuntimeError("RPi.GPIO not available. Are you running on Raspberry Pi?")

        self.pin = int(settings.get("pin", 4))
        self.poll_interval = float(settings.get("poll_interval", 0.05))
        self.on_change = on_change

        self._last = None

        GPIO.setwarnings(False)
        try:
            GPIO.setmode(GPIO.BCM)
        except Exception:
            pass

        GPIO.setup(self.pin, GPIO.IN)

    def run(self, stop_event):
        while not stop_event.is_set():
            val = 1 if GPIO.input(self.pin) else 0

            if self._last is None:
                self._last = val
                # inicijalno stanje pošalji odmah
                self.on_change(val)
            elif val != self._last:
                self._last = val
                self.on_change(val)

            time.sleep(self.poll_interval)

    def cleanup(self):
        try:
            GPIO.cleanup(self.pin)
        except Exception:
            pass