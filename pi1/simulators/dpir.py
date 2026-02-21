import time


class SimulationPir:
    """
    Pasivni simulator PIR-a.
    Ne generiše događaje sam od sebe.
    Događaji se okidaju ručno preko komponente (set_motion).
    """

    def __init__(self, settings: dict, on_change):
        self.on_change = on_change
        self.tick = float(settings.get("sim_tick", 0.2))

    def run(self, stop_event):
        # pošalji inicijalno stanje 0 samo jednom
        self.on_change(0)
        while not stop_event.is_set():
            time.sleep(self.tick)