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

    callback:
      callback(text4, settings)   # npr. "0459"
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

    # ---------------- PUBLIC API ----------------

    def start(self):
        """Pokreni countdown. Ako nit ne postoji, napravi je."""
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

        self._run_event.set()

    def set_seconds(self, seconds):
        """Postavi preostalo vreme (MMSS clamp)."""
        with self._lock:
            self.remaining = self._clamp(int(seconds))
            text4 = self._format_text4(self.remaining)

        self.callback(text4, self.settings)

    def add_seconds(self, seconds):
        """Dodaj/oduzmi sekunde (može i negativno)."""
        with self._lock:
            self.remaining = self._clamp(self.remaining + int(seconds))
            text4 = self._format_text4(self.remaining)

        self.callback(text4, self.settings)

    def shutdown(self):
        """Ugasi simulator nit."""
        self._run_event.clear()
        self._shutdown_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)


    def _clamp(self, seconds):
        # MMSS prikaz max 99:59
        return max(0, min(int(seconds), 99 * 60 + 59))

    def _format_text4(self, seconds):
        mm = seconds // 60
        ss = seconds % 60
        return f"{mm:02d}:{ss:02d}"

    def _loop(self):
        # odmah po startovanju niti javi trenutno stanje
        self.callback(self._format_text4(self.remaining), self.settings)

        last_tick = time.time()

        while not self._shutdown_event.is_set():
            now = time.time()

            # countdown radi samo nakon start()
            if self._run_event.is_set():
                while now - last_tick >= 1.0:
                    with self._lock:
                        if self.remaining > 0:
                            self.remaining -= 1
                        text4 = self._format_text4(self.remaining)

                    self.callback(text4, self.settings)
                    last_tick += 1.0
            else:
                # dok nije startovan, ne "troši" vreme
                last_tick = now

            # periodično emitovanje trenutnog stanja 
            with self._lock:
                text4 = self._format_text4(self.remaining)

            self.callback(text4, self.settings)
            time.sleep(self.period_s)