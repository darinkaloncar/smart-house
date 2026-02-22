import json
import time
import threading

from globals import batch, publish_limit, counter_lock, publish_event


class IrRemote:
    """
    Event-based IR remote:
    - publishuje MQTT kada se primi IR komanda (press event)
    """

    def __init__(self, settings, verbose: bool = False):
        self.settings = settings
        self.verbose = verbose
        self.simulated = settings.get("simulated", True)

        self._thread = None

        self.button_names = settings.get(
            "button_names",
            ["LEFT", "RIGHT", "UP", "DOWN", "OK", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "*", "#"]
        )
        self._button_set = {str(x) for x in self.button_names}

        if self.simulated:
            from simulators.ir import SimulationIrRemote
            self.impl = SimulationIrRemote(settings, on_press=self._on_ir_press)
        else:
            from sensors.ir import RealIrRemote
            self.impl = RealIrRemote(settings, on_press=self._on_ir_press)

    def _publish_ir_pressed(self, button_name: str):
        global publish_limit

        payload = {
            "measurement": "IR",
            "simulated": self.settings.get("simulated", True),
            "runs_on": self.settings["runs_on"],
            "name": self.settings["name"],
            "value": str(button_name),   # npr. OK, LEFT, 1...
            "event": "pressed"
        }

        topic = f"{self.settings['runs_on']}/{self.settings['name']}"
        with counter_lock:
            batch.append((topic, json.dumps(payload), 0, True))
            if len(batch) >= publish_limit:
                publish_event.set()

    def _on_ir_press(self, button_name: str):
        button_name = str(button_name)

        if self._button_set and button_name not in self._button_set:
            if self.verbose:
                print(f"[{self.settings['name']}] Ignored unknown IR button: {button_name}")
            return

        if self.verbose:
            ts = time.strftime("%H:%M:%S", time.localtime())
            print(f"[{self.settings['name']}] {ts} IR button={button_name} PRESSED")

        self._publish_ir_pressed(button_name)

    def start(self, stop_event):
        if self._thread and self._thread.is_alive():
            return self._thread

        self._thread = threading.Thread(
            target=self.impl.run,
            args=(stop_event,),
            daemon=True
        )
        self._thread.start()
        return self._thread

    def cleanup(self):
        try:
            if hasattr(self.impl, "cleanup"):
                self.impl.cleanup()
        except Exception:
            pass

    def press(self, button_name: str):
        self._on_ir_press(button_name)

    def press_many(self, buttons, inter_press_delay: float = 0.15):
        
        def _send():
            for b in buttons:
                if isinstance(b, str):
                    self.press(b)
                else:
                    self.press(str(b))
                time.sleep(max(0.01, float(inter_press_delay)))

        threading.Thread(target=_send, daemon=True).start()

    def send_code(self, code: str, inter_press_delay: float = 0.15):
  
        code = str(code)
        self.press_many(list(code), inter_press_delay=inter_press_delay)

    def buttons(self):
        return list(self.button_names)


def run_ir(settings, threads, stop_event, verbose: bool = False):
    ir = IrRemote(settings, verbose=verbose)
    th = ir.start(stop_event)
    threads.append(th)
    return ir