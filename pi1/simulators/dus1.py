import time
import threading
from collections import deque


class SimulationUltrasonic:
    """
    DUS simulator:
    - idle mode: salje konstantnu vrednost
    - scripted mode: odigra enter/exit sekvence kad ih trigerujes
    """

    def __init__(self, settings: dict, on_distance):
        self.on_distance = on_distance

        self.period_s = float(settings.get("period_s", 0.2))
        self.constant_distance = float(settings.get("constant_distance_cm", 200.0))
        self.min_distance = float(settings.get("min_distance_cm", 25.0))
        self.max_distance = float(settings.get("max_distance_cm", 220.0))

        self._current_distance = self.constant_distance
        self._scenario_queue = deque()
        self._lock = threading.Lock()

    def set_constant_distance(self, distance_cm: float):
        with self._lock:
            self.constant_distance = float(distance_cm)
            self._current_distance = self.constant_distance

    def _linspace(self, start: float, end: float, n: int):
        n = max(1, int(n))
        if n == 1:
            return [round(start, 1)]
        out = []
        for i in range(n):
            t = i / (n - 1)
            out.append(round(start + (end - start) * t, 1))
        return out

    def _build_enter_sequence(self, steps: int = 10):
        """
        Ulazak:
        osoba prilazi vratima/senzoru -> distanca opada
        npr. 200 -> 0
        """
        steps = max(2, int(steps))

        far = self.max_distance
        at_door = 0.0

        return self._linspace(far, at_door, steps)


    def _build_exit_sequence(self, steps: int = 10):
        """
        Izlazak:
        osoba kreće od vrata/senzora -> distanca raste
        npr. 0 -> 200
        """
        steps = max(2, int(steps))

        at_door = 0.0
        far = self.max_distance

        return self._linspace(at_door, far, steps)

    def simulate_enter(self, steps: int = 20):
        with self._lock:
            self._scenario_queue.append(self._build_enter_sequence(steps))

    def simulate_exit(self, steps: int = 20):
        with self._lock:
            self._scenario_queue.append(self._build_exit_sequence(steps))

    def run(self, stop_event):
        # inicijalna vrednost
        self.on_distance(self._current_distance)

        while not stop_event.is_set():
            next_seq = None

            with self._lock:
                if self._scenario_queue:
                    next_seq = self._scenario_queue.popleft()

            if next_seq is not None:
                for d in next_seq:
                    if stop_event.is_set():
                        break

                    with self._lock:
                        self._current_distance = d

                    self.on_distance(d)
                    time.sleep(self.period_s)

                # vrati se na konstantnu vrednost po zavrsetku scenarija
                with self._lock:
                    self._current_distance = self.constant_distance
                    idle_d = self._current_distance

                self.on_distance(idle_d)
            else:
                with self._lock:
                    d = self.constant_distance
                    self._current_distance = d

                self.on_distance(d)
                time.sleep(self.period_s)

    def cleanup(self):
        pass