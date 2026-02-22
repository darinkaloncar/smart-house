import time


def run_lcd_loop(settings, callback, stop_event, dht_snapshot_getter=None):
    from sensors.lcd.PCF8574 import PCF8574_GPIO
    from sensors.lcd.Adafruit_LCD1602 import Adafruit_CharLCD

    # probaj 0x27 pa 0x3F
    addr1 = int(settings.get("pcf8574_addr", 0x27))
    addr2 = int(settings.get("pcf8574a_addr", 0x3F))

    try:
        mcp = PCF8574_GPIO(addr1)
    except Exception:
        try:
            mcp = PCF8574_GPIO(addr2)
        except Exception:
            print("[LCD] I2C Address Error!")
            return

    lcd = Adafruit_CharLCD(pin_rs=0, pin_e=2, pins_db=[4, 5, 6, 7], GPIO=mcp)
    mcp.output(3, 1)  # backlight on
    lcd.begin(16, 2)

    switch_s = float(settings.get("switch_s", 3.0))
    refresh_s = float(settings.get("refresh_s", 1.0))
    names = settings.get("rotate_dhts", ["DHT1", "DHT2", "DHT3"])
    if not names:
        names = ["DHT1", "DHT2", "DHT3"]

    idx = 0
    last_switch = time.time()

    # poslednje prikazane linije (da ne salje/pisuje isto stalno)
    last_line1 = None
    last_line2 = None

    def show(line1, line2):
        try:
            lcd.clear()
            lcd.setCursor(0, 0)
            lcd.message(line1.ljust(16)[:16] + "\n" + line2.ljust(16)[:16])
        except Exception as e:
            print("[LCD] Write error:", e)

    try:
        while not stop_event.is_set():
            now = time.time()

            # rotacija DHT senzora
            if now - last_switch >= switch_s:
                idx = (idx + 1) % len(names)
                last_switch = now

            dht_name = names[idx]
            temp = None
            hum = None

            # uzmi trenutne vrednosti iz snapshot-a
            if dht_snapshot_getter is not None:
                try:
                    snap = dht_snapshot_getter() or {}
                    d = snap.get(dht_name, {})
                    temp = d.get("temperature")
                    hum = d.get("humidity")
                except Exception:
                    pass

            # format teksta za LCD
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

            # prikazi/salji samo kad se promeni tekst
            if line1 != last_line1 or line2 != last_line2:
                show(line1, line2)

                # callback moze da bude sa 2 ili 3 argumenta
                try:
                    callback(line1, line2, settings)
                except TypeError:
                    callback(line1, line2)

                last_line1 = line1
                last_line2 = line2

            time.sleep(refresh_s)

    finally:
        try:
            lcd.clear()
        except Exception:
            pass
        try:
            mcp.output(3, 0)  # backlight off
        except Exception:
            pass