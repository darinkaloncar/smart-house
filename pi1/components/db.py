import json
from globals import batch, publish_limit, counter_lock, publish_event

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
        global publish_limit

        payload = {
            "measurement": "BuzzerState",
            "simulated": self.settings["simulated"],
            "runs_on": self.settings["runs_on"],
            "name": self.settings["name"],
            "value": int(self._state)
        }

        with counter_lock:
            batch.append(("BuzzerState", json.dumps(payload), 0, True))

            if len(batch) >= publish_limit:
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

    def beep(self, ms: int):
        # START
        self._state = True
        self.impl.beep(ms)
        # END
        self._state = False
        self._publish_state()

    def is_on(self):
        return self._state
