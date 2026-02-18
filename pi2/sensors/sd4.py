import time

NUM = {
    " ": (0, 0, 0, 0, 0, 0, 0),
    "0": (1, 1, 1, 1, 1, 1, 0),
    "1": (0, 1, 1, 0, 0, 0, 0),
    "2": (1, 1, 0, 1, 1, 0, 1),
    "3": (1, 1, 1, 1, 0, 0, 1),
    "4": (0, 1, 1, 0, 0, 1, 1),
    "5": (1, 0, 1, 1, 0, 1, 1),
    "6": (1, 0, 1, 1, 1, 1, 1),
    "7": (1, 1, 1, 0, 0, 0, 0),
    "8": (1, 1, 1, 1, 1, 1, 1),
    "9": (1, 1, 1, 1, 0, 1, 1),
}


def run_sd4_loop(settings, callback, stop_event):
    """
    Real 4-digit 7-seg display loop (countdown timer).
    - segments: list/tuple of 8 GPIO pins (A..G + DOT)
    - digits: list/tuple of 4 GPIO pins (digit enables)
    - start_seconds: countdown start (default 300 = 5 min)
    - refresh_s: per-digit on-time (default 0.001)
    - blink_dot: blink dot on digit index 1 (default True)
    """
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)

    segments = tuple(settings.get("segments", (11, 4, 23, 8, 7, 10, 18, 25)))
    digits = tuple(settings.get("digits", (22, 27, 17, 24)))

    start_seconds = int(settings.get("start_seconds", 300))
    refresh_s = float(settings.get("refresh_s", 0.001))
    blink_dot = bool(settings.get("blink_dot", True))
    dot_digit = int(settings.get("dot_digit", 1))

    for p in segments:
        GPIO.setup(p, GPIO.OUT)
        GPIO.output(p, 0)

    for p in digits:
        GPIO.setup(p, GPIO.OUT)
        GPIO.output(p, 1)

    remaining = start_seconds
    last_tick = time.time()

    try:
        while not stop_event.is_set():
            # once per second
            now = time.time()
            if now - last_tick >= 1.0:
                if remaining > 0:
                    remaining -= 1
                last_tick = now

                mm = remaining // 60
                ss = remaining % 60
                text4 = f"{mm:02d}{ss:02d}"
                callback(text4, settings)

            mm = remaining // 60
            ss = remaining % 60
            text4 = f"{mm:02d}{ss:02d}"

            for di in range(4):
                ch = text4[di]
                pattern = NUM.get(ch, NUM[" "])

                for si in range(7):
                    GPIO.output(segments[si], pattern[si])

                # dot (segments[7]) blinking on chosen digit
                if len(segments) >= 8:
                    dot_on = blink_dot and (int(time.time()) % 2 == 0) and (di == dot_digit)
                    GPIO.output(segments[7], 1 if dot_on else 0)

                GPIO.output(digits[di], 0)
                time.sleep(refresh_s)
                GPIO.output(digits[di], 1)

    finally:
        GPIO.cleanup()
