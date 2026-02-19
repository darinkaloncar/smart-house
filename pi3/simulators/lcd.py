import time


def run_lcd_simulator(settings, callback, stop_event):
    switch_s = float(settings.get("switch_s", 3.0))
    refresh_s = float(settings.get("refresh_s", 1.0))

    dht1 = settings.get("dht1", {"temp": 24, "hum": 45})
    dht2 = settings.get("dht2", {"temp": 26, "hum": 40})
    dht3 = settings.get("dht3", {"temp": 25, "hum": 50})

    screens = [("DHT1", dht1), ("DHT2", dht2), ("DHT3", dht3)]
    idx = 0
    last_switch = time.time()

    while not stop_event.is_set():
        now = time.time()
        if now - last_switch >= switch_s:
            idx = (idx + 1) % len(screens)
            last_switch = now

        label, dht = screens[idx]
        line1 = f"{label} T:{dht['temp']}C"
        line2 = f"{label} H:{dht['hum']}%"

        callback(line1, line2)
        time.sleep(refresh_s)
