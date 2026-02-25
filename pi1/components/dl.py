import json
from globals import batch_fast, counter_lock, publish_event_fast

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

    def _publish_state(self):

        payload = {
            "measurement": "LightState",
            "simulated": self.settings["simulated"],
            "runs_on": self.settings["runs_on"],
            "name": self.settings["name"],
            "value": int(self._state)
        }
        topic = f"{self.settings['runs_on']}/{self.settings['name']}"
        with counter_lock:
            batch_fast.append((topic, json.dumps(payload), 0, False))
            publish_event_fast.set()

    def on(self):
        self._state = True
        if self.impl:
            self.impl.on()
        self._publish_state()

    def off(self):
        self._state = False
        if self.impl:
            self.impl.off()
        self._publish_state()

    def toggle(self):
        if self._state:
            self.off()
        else:
            self.on()

    def is_on(self):
        return self._state