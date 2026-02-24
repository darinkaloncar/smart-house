import time


def run_lcd_loop(settings, callback, stop_event, dht_snapshot_getter=None):
    print("[LCD] run_lcd_loop START")

    try:
        from sensors.lcdf.PCF8574 import PCF8574_GPIO
        from sensors.lcdf.Adafruit_LCD1602 import Adafruit_CharLCD
        print("[LCD] LCD libraries imported OK")
    except Exception as e:
        print("[LCD] Import error:", e)
        return

    # probaj 0x27 pa 0x3F
    addr1 = int(settings.get("pcf8574_addr", 0x27))
    addr2 = int(settings.get("pcf8574a_addr", 0x3F))


    mcp = None
    used_addr = None

    try:
        mcp = PCF8574_GPIO(addr1)
        used_addr = addr1
    except Exception as e1:
        try:
            mcp = PCF8574_GPIO(addr2)
            used_addr = addr2
        except Exception as e2:
            return

    try:
        lcd = Adafruit_CharLCD(pin_rs=0, pin_e=2, pins_db=[4, 5, 6, 7], GPIO=mcp)

        mcp.output(3, 1)  # backlight on

        lcd.begin(16, 2)
    except Exception as e:
        return

    switch_s = float(settings.get("switch_s", 3.0))
    refresh_s = float(settings.get("refresh_s", 1.0))
    names = settings.get("rotate_dhts", ["DHT1", "DHT2", "DHT3"])
    if not names:
        names = ["DHT1", "DHT2", "DHT3"]

    print(
        f"[LCD] Loop settings: switch_s={switch_s}, refresh_s={refresh_s}, "
        f"rotate_dhts={names}, used_addr={hex(used_addr) if used_addr is not None else 'N/A'}"
    )

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

    # Boot poruka da odmah vidiš da li LCD uopšte radi
    try:
        print("[LCD] Writing boot message...")
        lcd.clear()
        lcd.setCursor(0, 0)
        lcd.message("LCD booting...\nAddr " + hex(used_addr))
        print("[LCD] Boot message sent")
        time.sleep(2)
    except Exception as e:
        print("[LCD] Boot message error:", e)

    tick = 0

    try:
        while not stop_event.is_set():
            tick += 1
            now = time.time()

            print(f"[LCD] TICK {tick}")

            # rotacija DHT senzora
            if now - last_switch >= switch_s:
                idx = (idx + 1) % len(names)
                last_switch = now
                print(f"[LCD] Rotated sensor -> idx={idx}, name={names[idx]}")

            dht_name = names[idx]
            temp = None
            hum = None

            # uzmi trenutne vrednosti iz snapshot-a
            if dht_snapshot_getter is not None:
                try:
                    snap = dht_snapshot_getter() or {}
                    print(f"[LCD] Snapshot received: {snap}")

                    d = snap.get(dht_name, {})
                    temp = d.get("temperature")
                    hum = d.get("humidity")
                    print(f"[LCD] Parsed {dht_name}: temp={temp}, hum={hum}")
                except Exception as e:
                    print("[LCD] Snapshot getter error:", e)
            else:
                print("[LCD] dht_snapshot_getter is None -> using N/A")

            # format teksta za LCD
            try:
                temp_text = "N/A" if temp is None else f"{float(temp):.1f}C"
            except Exception as e:
                print("[LCD] Temp format error:", e)
                temp_text = "N/A"

            try:
                hum_text = "N/A" if hum is None else f"{float(hum):.1f}%"
            except Exception as e:
                hum_text = "N/A"

            line1 = f"{dht_name} T:{temp_text}"
            line2 = f"{dht_name} H:{hum_text}"

            print(f"[LCD] Prepared lines: '{line1}' | '{line2}'")

            # prikazi/salji samo kad se promeni tekst
            if line1 != last_line1 or line2 != last_line2:
                show(line1, line2)

                # callback moze da bude sa 2 ili 3 argumenta
                try:
                    callback(line1, line2, settings)
                except TypeError:
                    try:
                        callback(line1, line2)
                    except Exception as e:
                        print("[LCD] Callback error (2 args):", e)
                except Exception as e:
                    print("[LCD] Callback error (3 args):", e)

                last_line1 = line1
                last_line2 = line2
            else:
                print("[LCD] Content unchanged -> no LCD write")

            sleep_for = max(0.1, refresh_s)
            time.sleep(sleep_for)

    except Exception as e:
        print("[LCD] Loop fatal error:", e)

    finally:
        try:
            lcd.clear()
        except Exception as e:
            print("[LCD] lcd.clear() error:", e)

        try:
            mcp.output(3, 0)  # backlight off
        except Exception as e:
            print("[LCD] Backlight OFF error:", e)

