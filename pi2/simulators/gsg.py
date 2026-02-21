import time
import random
import queue

def run_gsg_simulator(cmd_q: "queue.Queue", callback, stop_event):
    """
    Čeka komande:
      - ("move", intensity)  -> jedan publish event sa velikim pomerajem
      - ("set", ax, ay, az, gx, gy, gz) -> ručno zadate vrednosti (jedan event)
    """
    rng = random.Random()

    while not stop_event.is_set():
        try:
            msg = cmd_q.get(timeout=0.1)
        except queue.Empty:
            continue

        if not msg:
            continue

        cmd = msg[0]

        if cmd == "move":
            intensity = float(msg[1]) if len(msg) >= 2 else 1.0

            # "mirno" + veliki trzaj
            ax = rng.uniform(-0.05, 0.05) + rng.uniform(-0.6, 0.6) * intensity
            ay = rng.uniform(-0.05, 0.05) + rng.uniform(-0.6, 0.6) * intensity
            az = 1.0 + rng.uniform(-0.10, 0.10) + rng.uniform(-0.4, 0.4) * intensity

            gx = rng.uniform(-2, 2) + rng.uniform(-120, 120) * intensity
            gy = rng.uniform(-2, 2) + rng.uniform(-120, 120) * intensity
            gz = rng.uniform(-2, 2) + rng.uniform(-180, 180) * intensity

            callback([ax, ay, az], [gx, gy, gz])

        elif cmd == "set":
            # ("set", ax, ay, az, gx, gy, gz)
            if len(msg) != 7:
                continue
            ax, ay, az, gx, gy, gz = map(float, msg[1:])
            callback([ax, ay, az], [gx, gy, gz])