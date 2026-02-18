import time

try:
    import RPi.GPIO as GPIO
except Exception:
    GPIO = None


class RealBuzzer:
    def __init__(self, settings: dict):
        if GPIO is None:
            raise RuntimeError("RPi.GPIO not available. Are you running on Raspberry Pi?")

        self.pin = int(settings.get("pin"))
        self.active_high = bool(settings.get("active_high", True))
        self.default_freq = int(settings.get("frequency", 440))
        self.default_duty = float(settings.get("duty_cycle", 50))

        self._state = False

        GPIO.setwarnings(False)

        try:
            GPIO.setmode(GPIO.BCM)
        except Exception:
            pass

        GPIO.setup(self.pin, GPIO.OUT)

        self.pwm = GPIO.PWM(self.pin, self.default_freq)
        self._initialized = False

    def on(self, pitch: int | None = None, duty_cycle: float | None = None):
        freq = pitch if pitch else self.default_freq
        dc = duty_cycle if duty_cycle else self.default_duty

        if not self._initialized:
            self.pwm.start(dc)
            self._initialized = True
        else:
            self.pwm.ChangeDutyCycle(dc)

        self.pwm.ChangeFrequency(freq)
        self._state = True

    def off(self):
        if self._initialized:
            self.pwm.stop()
            self._initialized = False
        self._state = False

    def beep(self, ms: int, pitch: int | None = None):
        self.on(pitch=pitch)
        time.sleep(ms / 1000.0)
        self.off()

    def is_on(self):
        return self._state

    def cleanup(self):
        try:
            self.off()
        finally:
            GPIO.cleanup(self.pin)
