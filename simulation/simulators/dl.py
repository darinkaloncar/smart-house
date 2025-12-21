class SimulationLED:
    def __init__(self, settings):
        self.pin = settings.get("pin")
        self.active_high = settings.get("active_high", True)
        self._state = False

    def on(self):
        self._state = True
        print(f"[SIM][DL] LED ON (pin={self.pin}, active_high={self.active_high})")

    def off(self):
        self._state = False
        print(f"[SIM][DL] LED OFF (pin={self.pin}, active_high={self.active_high})")

    def is_on(self):
        return self._state
