import time

try:
    import RPi.GPIO as GPIO
except Exception:
    GPIO = None


class RealUltrasonic:
    def __init__(self, settings: dict, on_distance):
        if GPIO is None:
            raise RuntimeError("RPi.GPIO not available. Are you running on Raspberry Pi?")

        self.on_distance = on_distance

        self.trigger_pin = int(settings.get("trig_pin", settings.get("trigger_pin")))
        self.echo_pin = int(settings.get("echo_pin"))
        self.period_s = float(settings.get("period_s", 0.2))
        self.timeout_s = float(settings.get("timeout_s", 0.02))

        GPIO.setwarnings(False)
        try:
            GPIO.setmode(GPIO.BCM)
        except Exception:
            pass

        GPIO.setup(self.trigger_pin, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(self.echo_pin, GPIO.IN)

    def _measure_once(self):
        GPIO.output(self.trigger_pin, GPIO.LOW)
        time.sleep(0.0002)

        GPIO.output(self.trigger_pin, GPIO.HIGH)
        time.sleep(0.00001)
        GPIO.output(self.trigger_pin, GPIO.LOW)

        # wait for echo to go high
        t0 = time.time()
        while GPIO.input(self.echo_pin) == 0:
            if (time.time() - t0) > self.timeout_s:
                return None

        pulse_start = time.time()

        # wait for echo to go low
        while GPIO.input(self.echo_pin) == 1:
            if (time.time() - pulse_start) > self.timeout_s:
                return None

        pulse_end = time.time()

        pulse_duration = pulse_end - pulse_start
        return (pulse_duration * 34300.0) / 2.0

    def run(self, stop_event):
        try:
            while not stop_event.is_set():
                d = self._measure_once()
                if d is not None:
                    self.on_distance(float(d))
                time.sleep(self.period_s)
        finally:
            self.cleanup()

    def cleanup(self):
        try:
            GPIO.cleanup(self.trigger_pin)
            GPIO.cleanup(self.echo_pin)
        except Exception:
            pass