import time

try:
    import RPi.GPIO as GPIO  
except Exception:
    GPIO = None


def run_dms_real(
    period_s: float,
    callback,       
    stop_event,
    keys,              
    row_pins,          
    col_pins,        
    debounce_s: float = 0.15
):
 
    if GPIO is None:
        raise RuntimeError("RPi.GPIO not available. Are you running on Raspberry Pi?")

    GPIO.setwarnings(False)
    try:
        GPIO.setmode(GPIO.BCM)
    except Exception:
        pass

    for rp in row_pins:
        GPIO.setup(rp, GPIO.OUT, initial=GPIO.LOW)

    for cp in col_pins:
        GPIO.setup(cp, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    if len(keys) == 4 and isinstance(keys[0], (list, tuple)):
        def idx_of(r, c): return r * 4 + c
    else:
        def idx_of(r, c): return r * 4 + c

    last_pressed_time = {} 
    prev_state = [[0]*4 for _ in range(4)]

    try:
        while not stop_event.is_set():
            for r, rp in enumerate(row_pins):
                GPIO.output(rp, GPIO.HIGH)
                time.sleep(0.0005)  #(0.5ms)

                for c, cp in enumerate(col_pins):
                    pressed = 1 if GPIO.input(cp) else 0

                    if pressed == 1 and prev_state[r][c] == 0:
                        now = time.time()
                        key = (r, c)
                        last = last_pressed_time.get(key, 0.0)
                        if (now - last) >= debounce_s:
                            last_pressed_time[key] = now
                            callback(idx_of(r, c), 1)

                    prev_state[r][c] = pressed

                GPIO.output(rp, GPIO.LOW)

            time.sleep(period_s)
    finally:
        try:
            for rp in row_pins:
                GPIO.cleanup(rp)
            for cp in col_pins:
                GPIO.cleanup(cp)
        except Exception:
            pass
