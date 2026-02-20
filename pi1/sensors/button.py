import time

try:
    import RPi.GPIO as GPIO  # type: ignore
except Exception:
    GPIO = None


def run_button_real(
    pin: int,
    callback,                 # callback(value: 0/1)
    stop_event,
    pull_up: bool = True,
    bouncetime_ms: int = 120
):
    if GPIO is None:
        raise RuntimeError("RPi.GPIO not available. Are you running on Raspberry Pi?")

    GPIO.setwarnings(False)
    try:
        GPIO.setmode(GPIO.BCM)
    except Exception:
        pass

    pud = GPIO.PUD_UP if pull_up else GPIO.PUD_DOWN
    GPIO.setup(pin, GPIO.IN, pull_up_down=pud)

    press_edge = GPIO.FALLING if pull_up else GPIO.RISING

    def _on_press(_channel):
        callback(1)

    GPIO.add_event_detect(pin, press_edge, callback=_on_press, bouncetime=bouncetime_ms)

    try:
        while not stop_event.is_set():
            time.sleep(0.05)
    finally:
        try:
            GPIO.remove_event_detect(pin)
        except Exception:
            pass
        try:
            GPIO.cleanup(pin)
        except Exception:
            pass
