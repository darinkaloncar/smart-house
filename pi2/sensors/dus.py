import time

try:
    import RPi.GPIO as GPIO 
except Exception:
    GPIO = None


def _measure_once(trigger_pin: int, echo_pin: int, timeout_s: float = 0.02):
    GPIO.output(trigger_pin, GPIO.LOW)
    time.sleep(0.0002)

    GPIO.output(trigger_pin, GPIO.HIGH)
    time.sleep(0.00001)
    GPIO.output(trigger_pin, GPIO.LOW)

    #  wait for echo to go high
    t0 = time.time()
    while GPIO.input(echo_pin) == 0:
        if (time.time() - t0) > timeout_s:
            return None

    pulse_start = time.time()

    # wait for echo to go low
    while GPIO.input(echo_pin) == 1:
        if (time.time() - pulse_start) > timeout_s:
            return None

    pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start
    return (pulse_duration * 34300.0) / 2.0


def run_ultrasonic_real(
    trigger_pin: int,
    echo_pin: int,
    period_s: float,
    callback,
    stop_event,
    timeout_s: float = 0.02,
):
    if GPIO is None:
        raise RuntimeError("RPi.GPIO not available. Are you running on Raspberry Pi?")

    GPIO.setwarnings(False)
    try:
        GPIO.setmode(GPIO.BCM)
    except Exception:
        pass

    GPIO.setup(trigger_pin, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(echo_pin, GPIO.IN)

    try:
        while not stop_event.is_set():
            d = _measure_once(trigger_pin, echo_pin, timeout_s=timeout_s)
            if d is not None:
                callback(float(d))
            time.sleep(period_s)
    finally:
        try:
            GPIO.cleanup(trigger_pin)
            GPIO.cleanup(echo_pin)
        except Exception:
            pass
