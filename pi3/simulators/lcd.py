import time


def run_lcd_simulator(settings, callback, stop_event, dht_snapshot_getter=None):
    switch_s = float(settings.get("switch_s", 3.0))
    refresh_s = float(settings.get("refresh_s", 1.0))

    names = settings.get("rotate_dhts", ["DHT1", "DHT2", "DHT3"])
    if not names:
        names = ["DHT1", "DHT2", "DHT3"]

    idx = 0
    last_switch = time.time()

    # poslednje poslato na LCD
    last_line1 = None
    last_line2 = None

    while not stop_event.is_set():
        now = time.time()

        # menja aktivni DHT na svakih switch_s sekundi
        if now - last_switch >= switch_s:
            idx = (idx + 1) % len(names)
            last_switch = now

        dht_name = names[idx]
        temp = None
        hum = None

        # uzmi trenutni snapshot
        if dht_snapshot_getter is not None:
            try:
                snap = dht_snapshot_getter() or {}
                d = snap.get(dht_name, {})
                temp = d.get("temperature")
                hum = d.get("humidity")
            except Exception:
                pass

        # formatiranje za LCD
        try:
            temp_text = "N/A" if temp is None else f"{float(temp):.1f}C"
        except Exception:
            temp_text = "N/A"

        try:
            hum_text = "N/A" if hum is None else f"{float(hum):.1f}%"
        except Exception:
            hum_text = "N/A"

        line1 = f"{dht_name} T:{temp_text}"
        line2 = f"{dht_name} H:{hum_text}"

        # salji samo kad se promeni prikaz
        if line1 != last_line1 or line2 != last_line2:
            callback(line1, line2)
            last_line1 = line1
            last_line2 = line2

        time.sleep(refresh_s)