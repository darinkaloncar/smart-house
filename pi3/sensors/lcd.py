import time


def run_lcd_loop(settings, callback, stop_event):
    from sensors.lcd.PCF8574 import PCF8574_GPIO
    from sensors.lcd.Adafruit_LCD1602 import Adafruit_CharLCD

    addr1 = int(settings.get("pcf8574_addr", 0x27))
    addr2 = int(settings.get("pcf8574a_addr", 0x3F))

    try:
        mcp = PCF8574_GPIO(addr1)
    except:
        try:
            mcp = PCF8574_GPIO(addr2)
        except:
            print("[LCD] I2C Address Error!")
            return

    lcd = Adafruit_CharLCD(pin_rs=0, pin_e=2, pins_db=[4, 5, 6, 7], GPIO=mcp)
    mcp.output(3, 1)
    lcd.begin(16, 2)

    switch_s = float(settings.get("switch_s", 3.0))
    refresh_s = float(settings.get("refresh_s", 1.0))

    #TODO change this to read from DHT sensors instead of settings
    dht1 = settings.get("dht1", {"temp": 24, "hum": 45})
    dht2 = settings.get("dht2", {"temp": 26, "hum": 40})
    dht3 = settings.get("dht3", {"temp": 25, "hum": 50})

    screens = [("DHT1", dht1), ("DHT2", dht2), ("DHT3", dht3)]
    idx = 0
    last_switch = time.time()

    def show(line1, line2):
        lcd.setCursor(0, 0)
        lcd.message(line1.ljust(16)[:16] + "\n")
        lcd.message(line2.ljust(16)[:16])

    try:
        while not stop_event.is_set():
            now = time.time()
            if now - last_switch >= switch_s:
                idx = (idx + 1) % len(screens)
                last_switch = now

            label, dht = screens[idx]
            line1 = f"{label} T:{dht['temp']}C"
            line2 = f"{label} H:{dht['hum']}%"

            show(line1, line2)
            callback(line1, line2, settings)
            time.sleep(refresh_s)

    finally:
        try:
            lcd.clear()
        except:
            pass
        try:
            mcp.output(3, 0)
        except:
            pass
