import time

COLOR_MAP = {
    "off":      (0, 0, 0),
    "white":    (1, 1, 1),
    "red":      (1, 0, 0),
    "green":    (0, 1, 0),
    "blue":     (0, 0, 1),
    "yellow":   (1, 1, 0),
    "purple":   (1, 0, 1),
    "lightBlue": (0, 1, 1),
}

def run_brgb_loop(settings, callback, stop_event):
    import RPi.GPIO as GPIO

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    pins = settings.get("pins", [12, 13, 19])
    r_pin, g_pin, b_pin = int(pins[0]), int(pins[1]), int(pins[2])

    period_s = float(settings.get("period_s", 1.0))
    sequence = settings.get("sequence", ["off", "white", "red", "green", "blue", "yellow", "purple", "lightBlue"])
    if not sequence:
        sequence = ["off"]

    for p in (r_pin, g_pin, b_pin):
        GPIO.setup(p, GPIO.OUT)

    def apply_color(name: str):
        rgb = COLOR_MAP.get(name, COLOR_MAP["off"])
        GPIO.output(r_pin, GPIO.HIGH if rgb[0] else GPIO.LOW)
        GPIO.output(g_pin, GPIO.HIGH if rgb[1] else GPIO.LOW)
        GPIO.output(b_pin, GPIO.HIGH if rgb[2] else GPIO.LOW)

    i = 0
    try:
        while not stop_event.is_set():
            color = sequence[i % len(sequence)]
            apply_color(color)
            callback(color, settings)
            i += 1
            time.sleep(period_s)
    finally:
        try:
            apply_color("off")
        except:
            pass
        GPIO.cleanup()
