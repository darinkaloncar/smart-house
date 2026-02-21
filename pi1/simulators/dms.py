import time


class SimulationDmsKeypad:
    """
    Ručni događaji idu kroz komponentu (DmsKeypad.press/release/tap/...).
    """

    def __init__(self, settings: dict, on_change):
        self.on_change = on_change
        self.tick = float(settings.get("sim_tick", 0.2))

    def run(self, stop_event):
        while not stop_event.is_set():
            time.sleep(self.tick)

    def cleanup(self):
        pass