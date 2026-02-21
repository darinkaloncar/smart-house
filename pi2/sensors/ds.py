import time

try:
    import RPi.GPIO as GPIO
except Exception:
    GPIO = None


class RealDoorSensor:

    def __init__(self, settings: dict, on_change):
        if GPIO is None:
            raise RuntimeError("RPi.GPIO not available. Are you running on Raspberry Pi?")

        self.pin = int(settings.get("pin"))
        self.pull_up = bool(settings.get("pull_up", True))
        self.poll_interval = float(settings.get("poll_interval", 0.03))
        self.on_change = on_change

        self._last = None

        GPIO.setwarnings(False)
        try:
            GPIO.setmode(GPIO.BCM)
        except Exception:
            pass

        pud = GPIO.PUD_UP if self.pull_up else GPIO.PUD_DOWN
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=pud)

    def _read_value(self) -> int:
        raw = GPIO.input(self.pin)

        # Ako koristimo pull-up:
        # raw=0 => pritisnuto => value=1
        # raw=1 => otpusteno => value=0
        if self.pull_up:
            return 1 if raw == 0 else 0

        # pull-down:
        # raw=1 => pritisnuto => value=1
        # raw=0 => otpusteno => value=0
        return 1 if raw == 1 else 0

    def run(self, stop_event):
        while not stop_event.is_set():
            val = self._read_value()

            if self._last is None:
                self._last = val
                self.on_change(val)  # init state
            elif val != self._last:
                self._last = val
                self.on_change(val)  # press/release

            time.sleep(self.poll_interval)

    def cleanup(self):
        try:
            GPIO.cleanup(self.pin)
        except Exception:
            pass