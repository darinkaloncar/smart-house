import threading
from publisher import start_publisher_thread
from settings.settings import load_settings

from components.brgb import BrgbLed
from components.ir import IrRemote
from components.lcd import run_lcd

from components.dht1 import run_dht1
from components.dht2 import run_dht2
from components.dpir3 import run_dpir3

try:
    import RPi.GPIO as GPIO  # type: ignore
    GPIO.setmode(GPIO.BCM)
except Exception:
    pass


def _run_if_present(settings, key, runner, threads, stop_event):
    if key not in settings:
        print(f"[WARN] Missing settings for {key}")
        return None
    return runner(settings[key], threads, stop_event)


def print_help():
    print("""
Commands:
  status
  exit

  ir <BUTTON>             e.g. ir OK | ir LEFT | ir 1
  irseq <DIGITS>          e.g. irseq 1234
  irmany <B1,B2,...>      e.g. irmany 1,2,3,OK

  brgb <COLOR>            e.g. brgb red | brgb blue | brgb off
  brgb off
  brgb list
""")


if __name__ == "__main__":
    print("Starting PI3")

    settings = load_settings()
    threads = []
    stop_event = threading.Event()

    start_publisher_thread()

    _run_if_present(settings, "DHT1", run_dht1, threads, stop_event)
    _run_if_present(settings, "DHT2", run_dht2, threads, stop_event)

    ir = None
    if "IR" in settings:
        try:
            ir = IrRemote(settings["IR"], verbose=True)
            th_ir = ir.start(stop_event)
            threads.append(th_ir)
        except Exception as e:
            print(f"[WARN] IR failed to start: {e}")
    else:
        print("[WARN] Missing settings for IR")

    brgb = None
    if "BRGB" in settings:
        try:
            brgb = BrgbLed(settings["BRGB"], verbose=True)
            th_brgb = brgb.start(stop_event)
            threads.append(th_brgb)
        except Exception as e:
            print(f"[WARN] BRGB failed to start: {e}")
    else:
        print("[WARN] Missing settings for BRGB")

    _run_if_present(settings, "LCD", run_lcd, threads, stop_event)
    _run_if_present(settings, "DPIR3", run_dpir3, threads, stop_event)

    print_help()

    try:
        while True:
            cmd = input("input> ").strip()
            if not cmd:
                continue

            if cmd == "exit":
                break

            if cmd == "status":
                for k in ["DHT1", "DHT2", "IR", "BRGB", "LCD", "DPIR3"]:
                    if k in settings:
                        s = settings[k]
                        print(
                            f"{k}: simulated={s.get('simulated', True)} "
                            f"runs_on={s.get('runs_on', 'PI3')} name={s.get('name', k)}"
                        )
                if ir is not None:
                    print(f"IR buttons: {ir.buttons()}")
                if brgb is not None:
                    print(f"BRGB colors: {brgb.colors()}")
                continue

            # -------- IR commands --------
            if cmd.lower().startswith("ir "):
                if ir is None:
                    print("IR is not initialized.")
                    continue
                btn = cmd[3:].strip().upper()
                if not btn:
                    print("Usage: ir <BUTTON>")
                    continue
                ir.press(btn)
                continue

            if cmd.lower().startswith("irseq "):
                if ir is None:
                    print("IR is not initialized.")
                    continue
                seq = cmd[6:].strip()
                if not seq:
                    print("Usage: irseq <DIGITS>")
                    continue
                ir.send_code(seq)
                continue

            if cmd.lower().startswith("irmany "):
                if ir is None:
                    print("IR is not initialized.")
                    continue
                raw = cmd[7:].strip()
                if not raw:
                    print("Usage: irmany <B1,B2,...>")
                    continue
                buttons = [x.strip().upper() for x in raw.split(",") if x.strip()]
                ir.press_many(buttons)
                continue

            # -------- BRGB commands --------
            if cmd.lower() == "brgb list":
                if brgb is None:
                    print("BRGB is not initialized.")
                    continue
                print("Available BRGB colors:", ", ".join(brgb.colors()))
                continue

            if cmd.lower() == "brgb off":
                if brgb is None:
                    print("BRGB is not initialized.")
                    continue
                brgb.off()
                continue

            if cmd.lower().startswith("brgb "):
                if brgb is None:
                    print("BRGB is not initialized.")
                    continue
                color = cmd[5:].strip()
                if not color:
                    print("Usage: brgb <COLOR>")
                    continue
                brgb.set_color(color)
                continue

            print("Wrong input")

    except KeyboardInterrupt:
        print("Stopping")

    finally:
        stop_event.set()
        for t in threads:
            t.join(timeout=1)

        if ir is not None:
            try:
                ir.cleanup()
            except Exception:
                pass

        if brgb is not None:
            try:
                brgb.cleanup()
            except Exception:
                pass

        print("Safely Stopped")