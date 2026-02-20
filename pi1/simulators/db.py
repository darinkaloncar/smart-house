import time

class SimulationBuzzer:
    def __init__(self, settings):
        self.pin = settings.get("pin")
        self.active_high = settings.get("active_high", True)
        self._state = False

    def on(self):
        self._state = True
        print(f"[SIM][DB] BUZZER ON (pin={self.pin}, active_high={self.active_high})")

    def off(self):
        self._state = False
        print(f"[SIM][DB] BUZZER OFF (pin={self.pin}, active_high={self.active_high})")

    def beep(self, ms: int):
        print(f"[SIM][DB] BEEP {ms}ms")
        self.on()
        time.sleep(ms / 1000.0)
        self.off()

    def is_on(self):
        return self._state