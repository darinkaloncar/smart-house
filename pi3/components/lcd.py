import json
import threading

from globals import batch, publish_limit, counter_lock, publish_event
from simulators.lcd import run_lcd_simulator


def lcd_callback(line1, line2, settings):
    global publish_limit

    payload = {
        "measurement": "LCD",
        "simulated": settings.get("simulated", True),
        "runs_on": settings["runs_on"],
        "name": settings["name"],
        "line1": str(line1),
        "line2": str(line2),
        "value": f"{line1} | {line2}" 
        
    }
    topic = f"{settings['runs_on']}/{settings['name']}"
    with counter_lock:
        batch.append((topic, json.dumps(payload), 0, True))
        if len(batch) >= publish_limit:
            publish_event.set()


def run_lcd(settings, threads, stop_event):
    simulated = settings.get("simulated", True)

    if simulated:
        th = threading.Thread(
            target=run_lcd_simulator,
            args=(settings, lambda a, b: lcd_callback(a, b, settings), stop_event),
            daemon=True
        )
    else:
        from sensors.lcd import run_lcd_loop
        th = threading.Thread(
            target=run_lcd_loop,
            args=(settings, lcd_callback, stop_event),
            daemon=True
        )

    th.start()
    threads.append(th)
