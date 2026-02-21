import json
import time
import threading

from globals import batch, publish_limit, counter_lock, publish_event


class DmsKeypad:
    """
    - čuva stanje svih tastera (pressed/released)
    - publishuje MQTT na promenu (press/release)
    - podržava ručno tap/press/release iz konzole

    keys može biti:
      - int (broj tastera)
      - flat lista ["1","2",...]
      - 2D lista [["1","2","3","A"], ...]
    """

    def __init__(self, settings, verbose: bool = False):
        self.settings = settings
        self.verbose = verbose
        self.simulated = settings.get("simulated", True)

        self.keys_layout = settings.get("keys", 16)
        self._keys_flat = self._flatten_keys(self.keys_layout)
        self._states = [0] * len(self._keys_flat)  # 0=release, 1=press

        self._thread = None
        self._lock = threading.Lock()

        if self.simulated:
            from simulators.dms import SimulationDmsKeypad
            self.impl = SimulationDmsKeypad(settings, on_change=self._on_key_change)
        else:
            from sensors.dms import RealDmsKeypad
            self.impl = RealDmsKeypad(settings, on_change=self._on_key_change)

    def _flatten_keys(self, keys):
        if isinstance(keys, int):
            return [str(i) for i in range(keys)]

        if isinstance(keys, (list, tuple)):
            if len(keys) == 0:
                return []

            if isinstance(keys[0], (list, tuple)):  # 2D
                flat = []
                for row in keys:
                    for item in row:
                        flat.append(str(item))
                return flat

            return [str(x) for x in keys]

        raise TypeError(f"Unsupported keys type: {type(keys)}")

    def _key_label(self, idx: int) -> str:
        if 0 <= idx < len(self._keys_flat):
            return self._keys_flat[idx]
        return str(idx)

    def _find_index_by_label(self, key_label: str) -> int:
        key_label = str(key_label)
        for i, k in enumerate(self._keys_flat):
            if str(k) == key_label:
                return i
        raise ValueError(f"Key '{key_label}' not found in DMS layout")

    def _publish_key_state(self, idx: int, state: int):
        global publish_limit

        payload = {
            "measurement": "DMS",
            "simulated": self.settings["simulated"],
            "runs_on": self.settings["runs_on"],
            "name": self.settings["name"],
            "key_index": int(idx),
            "key": self._key_label(idx),
            "state": int(state)  # 1=press, 0=release
        }

        topic = f"{self.settings['runs_on']}/{self.settings['name']}"
        with counter_lock:
            batch.append((topic, json.dumps(payload), 0, True))
            if len(batch) >= publish_limit:
                publish_event.set()

    def _on_key_change(self, idx: int, state: int):
        idx = int(idx)
        state = 1 if state else 0

        if idx < 0 or idx >= len(self._states):
            return

        with self._lock:
            if self._states[idx] == state:
                return  # samo na promenu
            self._states[idx] = state

        if self.verbose:
            ts = time.strftime("%H:%M:%S", time.localtime())
            label = "PRESSED" if state else "RELEASED"
            print(f"[{self.settings['name']}] {ts} key={self._key_label(idx)} idx={idx} {label}")

        self._publish_key_state(idx, state)

    def start(self, stop_event):
        if self._thread and self._thread.is_alive():
            return self._thread

        self._thread = threading.Thread(
            target=self.impl.run,
            args=(stop_event,),
            daemon=True
        )
        self._thread.start()
        return self._thread

    def cleanup(self):
        try:
            if hasattr(self.impl, "cleanup"):
                self.impl.cleanup()
        except Exception:
            pass

    def press(self, idx: int):
        self._on_key_change(idx, 1)

    def release(self, idx: int):
        self._on_key_change(idx, 0)

    def tap(self, idx: int, duration: float = 0.08):
        def _pulse():
            self.press(idx)
            time.sleep(max(0.01, float(duration)))
            self.release(idx)

        threading.Thread(target=_pulse, daemon=True).start()

    def press_key(self, key_label: str):
        self.press(self._find_index_by_label(key_label))

    def release_key(self, key_label: str):
        self.release(self._find_index_by_label(key_label))

    def tap_key(self, key_label: str, duration: float = 0.08):
        self.tap(self._find_index_by_label(key_label), duration)

    def enter_pin(self, pin: str, inter_key_delay: float = 0.15, press_duration: float = 0.08):
        """
        Simulira unos npr. "1234" kao uzastopne tap-ove.
        """
        pin = str(pin)

        def _enter():
            for ch in pin:
                self.tap_key(ch, duration=press_duration)
                time.sleep(max(0.01, float(inter_key_delay)))

        threading.Thread(target=_enter, daemon=True).start()

    def read_states(self):
        with self._lock:
            return list(self._states)

    def is_pressed(self, idx: int) -> bool:
        with self._lock:
            if 0 <= idx < len(self._states):
                return bool(self._states[idx])
            return False

    def key_count(self) -> int:
        return len(self._states)

    def keys(self):
        return list(self._keys_flat)