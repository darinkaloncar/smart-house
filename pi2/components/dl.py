import json
from globals import batch, publish_counter, publish_limit, counter_lock, publish_event

class DoorLight:
    def __init__(self, settings):
        self.settings = settings
        self.simulated = settings.get("simulated", True)
        self._state = False

        if not self.simulated:
            from simulation.sensors.dl import RealLED
            self.impl = RealLED(settings)
        else:
            from simulation.simulators.dl import SimulationLED
            self.impl = SimulationLED(settings)

    def _publish_state(self):
        global publish_counter, publish_limit

        payload = {
            "measurement": "LightState",
            "simulated": self.settings["simulated"],
            "runs_on": self.settings["runs_on"],
            "name": self.settings["name"],
            "value": int(self._state)
        }

        with counter_lock:
            batch.append(("LightState", json.dumps(payload), 0, True))
            publish_counter += 1
            if publish_counter >= publish_limit:
                publish_event.set()

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