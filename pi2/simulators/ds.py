import time


class SimulationDoorSensor:
    """
    Pasivni simulator za DS:
    - ne generiše random događaje
    - inicijalno pošalje state=0
    - press/release se okidaju ručno preko DoorSensor.press/release/trigger
    """

    def __init__(self, settings: dict, on_change):
        self.on_change = on_change
        self.tick = float(settings.get("sim_tick", 0.2))

    def run(self, stop_event):
        # inicijalno stanje
        self.on_change(0)

        # idle loop
        while not stop_event.is_set():
            time.sleep(self.tick)

    def cleanup(self):
        pass