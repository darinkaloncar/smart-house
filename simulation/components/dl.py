class DoorLight:
    def __init__(self, settings):
        self.settings = settings
        self.simulated = settings.get("simulated", True)
        self._state = False

        if not self.simulated:
            from sensors.dl import RealLED
            self.impl = RealLED(settings)
        else:
            from simulators.dl import SimulationLED
            self.impl = SimulationLED(settings)

    def on(self):
        self._state = True
        if self.impl: self.impl.on()

    def off(self):
        self._state = False
        if self.impl: self.impl.off()

    def toggle(self):
        if self._state:
            self.off()
        else:
            self.on()

    def is_on(self):
        return self._state
