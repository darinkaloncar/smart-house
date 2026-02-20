import time

try:
    import RPi.GPIO as GPIO  
except Exception:
    GPIO = None


def run_pir_real(pin: int, callback, stop_event, poll_interval: float = 0.05):
    if GPIO is None:
        raise RuntimeError("RPi.GPIO not available. Are you running on Raspberry Pi?")

    GPIO.setwarnings(False)
    try:
        GPIO.setmode(GPIO.BCM)
    except Exception:
        pass

    GPIO.setup(pin, GPIO.IN)

    last = None
    while not stop_event.is_set():
        val = 1 if GPIO.input(pin) else 0

        if last is None:
            last = val
            callback(val)           # immdeiately publish init state
        elif val != last:
            last = val
            callback(val)

        time.sleep(poll_interval)

    try:
        GPIO.cleanup(pin)
    except Exception:
        pass
