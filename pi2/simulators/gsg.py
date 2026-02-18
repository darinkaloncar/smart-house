import time
import random


def run_gsg_simulator(period_s, callback, stop_event):
    rng = random.Random()

    ax, ay, az = 0.0, 0.0, 1.0
    gx, gy, gz = 0.0, 0.0, 0.0

    def clamp(x, lo, hi):
        return lo if x < lo else hi if x > hi else x

    while not stop_event.is_set():
        ax += rng.uniform(-0.02, 0.02)
        ay += rng.uniform(-0.02, 0.02)
        az += rng.uniform(-0.02, 0.02)

        gx += rng.uniform(-2.0, 2.0)
        gy += rng.uniform(-2.0, 2.0)
        gz += rng.uniform(-2.0, 2.0)

        # Occasionally simulate movement
        if rng.random() < 0.10:
            ax += rng.uniform(-0.3, 0.3)
            ay += rng.uniform(-0.3, 0.3)
            az += rng.uniform(-0.2, 0.2)

            gx += rng.uniform(-80, 80)
            gy += rng.uniform(-80, 80)
            gz += rng.uniform(-120, 120)

        ax = clamp(ax, -2.0, 2.0)
        ay = clamp(ay, -2.0, 2.0)
        az = clamp(az, -2.0, 2.0)

        gx = clamp(gx, -250.0, 250.0)
        gy = clamp(gy, -250.0, 250.0)
        gz = clamp(gz, -250.0, 250.0)

        callback([float(ax), float(ay), float(az)], [float(gx), float(gy), float(gz)])
        time.sleep(float(period_s))
