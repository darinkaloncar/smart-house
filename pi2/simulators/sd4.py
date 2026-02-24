import time
import threading


class SD4Simulator:
    """
    Minimal SD4 simulator (MMSS countdown).

    API:
      - start()
      - set_seconds(seconds)
      - add_seconds(seconds)
      - shutdown()

    + blink support:
      - set_blinking(flag)
      - is_blinking()

    callback:
      callback(text4, settings)   # npr. "04:59"
    """

    def __init__(self, settings, callback=None):
        self.settings = dict(settings or {})
        self.callback = callback if callback is not None else (lambda text4, settings: None)

        start_seconds = int(self.settings.get("start_seconds", 300))
        self.period_s = float(self.settings.get("period_s", 0.2))  # koliko često emituje stanje

        self.remaining = self._clamp(start_seconds)

        self._lock = threading.Lock()
        self._shutdown_event = threading.Event()
        self._run_event = threading.Event()   # set => countdown radi
        self._thread = None

        self.blinking = False
        self._blink_visible = True
        self._last_blink_toggle = time.time()
        self._blink_interval_s = float(self.settings.get("blink_interval_s", 0.5))

    # ---------------- PUBLIC API ----------------

    def start(self):
        """Pokreni countdown. Ako nit ne postoji, napravi je."""
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

        with self._lock:
            self._run_event.set()
            self._last_blink_toggle = time.time()

    def set_seconds(self, seconds):
        """Postavi preostalo vreme (MMSS clamp). Gasi blink."""
        with self._lock:
            self.remaining = self._clamp(int(seconds))
            self.blinking = False
            self._blink_visible = True
            self._last_blink_toggle = time.time()
            text4 = self._format_text4(self.remaining)

        self.callback(text4, self.settings)

    def add_seconds(self, seconds):
        """Dodaj/oduzmi sekunde (može i negativno). Ako doda >0, gasi blink."""
        with self._lock:
            self.remaining = self._clamp(self.remaining + int(seconds))

            # Ako je bio blink i sada opet ima vremena ugasi blink
            if self.remaining > 0:
                self.blinking = False
                self._blink_visible = True
                self._last_blink_toggle = time.time()

            text4 = self._format_text4(self.remaining)

        self.callback(text4, self.settings)

    def set_blinking(self, flag: bool):
        with self._lock:
            self.blinking = bool(flag)
            self._blink_visible = True
            self._last_blink_toggle = time.time()

    def is_blinking(self) -> bool:
        with self._lock:
            return bool(self.blinking)

    def shutdown(self):
        """Ugasi simulator nit."""
        self._run_event.clear()
        self._shutdown_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    # ---------------- INTERNAL ----------------

    def _clamp(self, seconds):
        # MMSS prikaz max 99:59
        return max(0, min(int(seconds), 99 * 60 + 59))

    def _format_text4(self, seconds):
        mm = seconds // 60
        ss = seconds % 60
        return f"{mm:02d}:{ss:02d}"

    def _current_display_text(self):
        """
        Ako blinkuje na 00:00:
          - naizmenično prikazuj '00:00' i prazno
        Inače:
          - normalan prikaz remaining
        """
        with self._lock:
            if self.blinking and self.remaining == 0:
                return "00:00" if self._blink_visible else "     "
            return self._format_text4(self.remaining)

    def _loop(self):
        # odmah po startovanju niti javi trenutno stanje
        self.callback(self._format_text4(self.remaining), self.settings)

        last_tick = time.time()

        while not self._shutdown_event.is_set():
            now = time.time()

            # countdown radi samo nakon start()
            if self._run_event.is_set():
                while now - last_tick >= 1.0:
                    reached_zero_now = False

                    with self._lock:
                        if self.remaining > 0:
                            self.remaining -= 1
                            if self.remaining == 0:
                                reached_zero_now = True

                        # Kad dođe do 0, uključi blink i zaustavi countdown
                        if reached_zero_now:
                            self.blinking = True
                            self._blink_visible = True
                            self._last_blink_toggle = time.time()
                            self._run_event.clear()

                    last_tick += 1.0
            else:
                # dok nije startovan, ne "troši" vreme
                last_tick = now

            # blink toggle
            with self._lock:
                if self.blinking and self.remaining == 0:
                    if (now - self._last_blink_toggle) >= self._blink_interval_s:
                        self._blink_visible = not self._blink_visible
                        self._last_blink_toggle = now

            # periodično emitovanje trenutnog stanja
            text4 = self._current_display_text()
            self.callback(text4, self.settings)

            time.sleep(self.period_s)