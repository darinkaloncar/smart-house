import time
from typing import Optional

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

    def on(self, pitch: Optional[int] = None, duty_cycle: Optional[float] = None):
        freq = self.default_freq if pitch is None else int(pitch)
        dc = self.default_duty if duty_cycle is None else float(duty_cycle)

        # Safety clamp for PWM duty cycle
        if dc < 0:
            dc = 0.0
        elif dc > 100:
            dc = 100.0

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

    def beep(self, ms: int, pitch: Optional[int] = None):
        self.on(pitch=pitch)
        time.sleep(max(0, int(ms)) / 1000.0)
        self.off()

    def is_on(self) -> bool:
        return self._state

    def cleanup(self):
        try:
            self.off()
        finally:
            if GPIO is not None:
                GPIO.cleanup(self.pin)