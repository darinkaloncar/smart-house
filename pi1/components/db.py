import json
from globals import batch_fast, counter_lock, publish_event_fast

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

    def _publish_state(self):

        payload = {
            "measurement": "BuzzerState",
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

    def beep(self, ms: int):
        # START
        self._state = True
        self.impl.beep(ms)
        # END
        self._state = False
        self._publish_state()

    def is_on(self):
        return self._state
