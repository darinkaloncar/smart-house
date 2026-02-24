import time
import threading


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


class SD4Timer:
    """
    4-digit 7-seg countdown (MM:SS), multiplexed display.
    + blinking when time reaches 00:00
    """

    def __init__(self, settings, callback=None):
        self.settings = dict(settings or {})
        self.callback = callback if callback is not None else (lambda text4, settings: None)

        self.segments = tuple(self.settings.get("segments", (11, 4, 23, 8, 7, 10, 18, 25)))  # A..G + DOT
        self.digits = tuple(self.settings.get("digits", (22, 27, 17, 24)))  # D1..D4

        self.refresh_s = float(self.settings.get("refresh_s", 0.001))
        self.blink_dot = bool(self.settings.get("blink_dot", True))
        self.dot_digit = int(self.settings.get("dot_digit", 1))

        self.segment_on = int(self.settings.get("segment_on", 1))
        self.segment_off = 0 if self.segment_on == 1 else 1
        self.digit_on = int(self.settings.get("digit_on", 0))
        self.digit_off = 0 if self.digit_on == 1 else 1

        start_seconds = int(self.settings.get("start_seconds", 300))
        self.remaining = self._clamp(start_seconds)

        self._lock = threading.Lock()
        self._shutdown_event = threading.Event()
        self._run_event = threading.Event()
        self._thread = None
        self._gpio_ready = False
        self.blinking = False

    # ---------------- PUBLIC API ----------------

    def start(self):
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
        self._run_event.set()

    def set_seconds(self, seconds):
        with self._lock:
            self.remaining = self._clamp(int(seconds))
            self.blinking = False
            text4 = self._format_text4(self.remaining)
        self.callback(text4, self.settings)

    def add_seconds(self, seconds):
        with self._lock:
            self.remaining = self._clamp(self.remaining + int(seconds))
            text4 = self._format_text4(self.remaining)
        self.callback(text4, self.settings)

    def is_blinking(self):
        with self._lock:
            return bool(self.blinking)

    def set_blinking(self, value: bool):
        with self._lock:
            self.blinking = bool(value)
            text4 = self._format_text4(self.remaining)
        self.callback(text4, self.settings)

    def shutdown(self):
        self._run_event.clear()
        self._shutdown_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    # ---------------- INTERNAL ----------------

    def _clamp(self, seconds):
        return max(0, min(int(seconds), 99 * 60 + 59))

    def _format_text4(self, seconds):
        mm = seconds // 60
        ss = seconds % 60
        return f"{mm:02d}:{ss:02d}"

    def _all_digits_off(self, GPIO):
        for p in self.digits:
            GPIO.output(p, self.digit_off)

    def _set_segment(self, GPIO, pin, on):
        GPIO.output(pin, self.segment_on if on else self.segment_off)

    def _setup_gpio(self, GPIO):
        GPIO.setmode(GPIO.BCM)

        for p in self.segments:
            GPIO.setup(p, GPIO.OUT)
            GPIO.output(p, self.segment_off)

        for p in self.digits:
            GPIO.setup(p, GPIO.OUT)
            GPIO.output(p, self.digit_off)

        self._gpio_ready = True

    def _cleanup_gpio(self, GPIO):
        if not self._gpio_ready:
            return
        try:
            self._all_digits_off(GPIO)
            for p in self.segments:
                GPIO.output(p, self.segment_off)
            GPIO.cleanup(list(self.segments) + list(self.digits))
        except Exception:
            pass

    def _loop(self):
        import RPi.GPIO as GPIO

        self._setup_gpio(GPIO)

        # odmah po startu javi stanje
        self.callback(self._format_text4(self.remaining), self.settings)

        last_tick = time.time()
        last_callback_text = None

        try:
            while not self._shutdown_event.is_set():
                now = time.time()

                # countdown
                if self._run_event.is_set():
                    while now - last_tick >= 1.0:
                        with self._lock:
                            if self.remaining > 0:
                                self.remaining -= 1
                                if self.remaining == 0:
                                    self.blinking = True  # uključi blinking kad istekne
                        last_tick += 1.0
                else:
                    last_tick = now

                # priprema prikaza
                with self._lock:
                    text_full = self._format_text4(self.remaining)
                    blinking = self.blinking

                # blinking smejivanje
                if blinking and self.remaining == 0:
                    visible = (int(now * 2) % 2 == 0)  # menja na oko 0.5s
                    render_text = text_full if visible else "    "
                    callback_text = render_text
                else:
                    render_text = text_full
                    callback_text = text_full

                # callback samo kad se promeni
                if callback_text != last_callback_text:
                    self.callback(callback_text, self.settings)
                    last_callback_text = callback_text

                for di in range(4):
                    if self._shutdown_event.is_set():
                        break

                    self._all_digits_off(GPIO)

                    if len(render_text) == 5:
                        ch = render_text[[0, 1, 3, 4][di]]
                        colon_enabled = True
                    else:
                        ch = render_text[di]
                        colon_enabled = False

                    pattern = NUM.get(ch, NUM[" "])

                    for si in range(7):
                        self._set_segment(GPIO, self.segments[si], pattern[si] == 1)

                    # dot/colon segment
                    if len(self.segments) >= 8:
                        if colon_enabled:
                            dot_on = self.blink_dot and (int(now) % 2 == 0) and (di == self.dot_digit)
                        else:
                            dot_on = False
                        self._set_segment(GPIO, self.segments[7], dot_on)

                    GPIO.output(self.digits[di], self.digit_on)
                    time.sleep(self.refresh_s)
                    GPIO.output(self.digits[di], self.digit_off)

        finally:
            self._cleanup_gpio(GPIO)