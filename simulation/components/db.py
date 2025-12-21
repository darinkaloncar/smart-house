import time

class DoorBuzzer:
    def __init__(self, settings):
        self.settings = settings
        self.simulated = settings.get("simulated", True)
        self._state = False

        if not self.simulated:
            from sensors.db import RealBuzzer
            self.impl = RealBuzzer(settings)
        else:
            from simulators.db import SimulationBuzzer
            self.impl = SimulationBuzzer(settings)

    def on(self):
        self._state = True
        if self.impl: self.impl.on()

    def off(self):
        self._state = False
        if self.impl: self.impl.off()

    def beep(self, ms: int):
        self._state = True
        self.impl.beep(ms)
        self._state = False

    def is_on(self):
        return self._state