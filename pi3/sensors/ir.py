from datetime import datetime
import time

try:
    import RPi.GPIO as GPIO
except Exception:
    GPIO = None


class RealIrRemote:
    """
    Real IR receiver:
    - dekodira komande i šalje on_press(button_name)
    """

    def __init__(self, settings: dict, on_press):
        if GPIO is None:
            raise RuntimeError("RPi.GPIO not available. Are you running on Raspberry Pi?")

        self.settings = settings
        self.on_press = on_press

        self.pin = int(settings.get("pin", 17))

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN)

        buttons = [
            0x300ff22dd, 0x300ffc23d, 0x300ff629d, 0x300ffa857, 0x300ff9867,
            0x300ffb04f, 0x300ff6897, 0x300ff02fd, 0x300ff30cf, 0x300ff18e7,
            0x300ff7a85, 0x300ff10ef, 0x300ff38c7, 0x300ff5aa5, 0x300ff42bd,
            0x300ff4ab5, 0x300ff52ad
        ]
        button_names = [
            "LEFT", "RIGHT", "UP", "DOWN", "2", "3", "1", "OK", "4", "5",
            "6", "7", "8", "9", "*", "0", "#"
        ]

        self.code_to_name = {hex(buttons[i]): button_names[i] for i in range(len(button_names))}

    def _get_binary(self, stop_event):
        num1s = 0
        binary = 1
        command = []
        previous_value = 0
        value = GPIO.input(self.pin)

        # čekaj start (LOW), ali proveravaj stop
        while value and not stop_event.is_set():
            time.sleep(0.0001)
            value = GPIO.input(self.pin)

        if stop_event.is_set():
            return None

        start_time = datetime.now()

        while not stop_event.is_set():
            if previous_value != value:
                now = datetime.now()
                pulse_time = now - start_time
                start_time = now
                command.append((previous_value, pulse_time.microseconds))

            if value:
                num1s += 1
            else:
                num1s = 0

            if num1s > 10000:
                break

            previous_value = value
            value = GPIO.input(self.pin)

        if stop_event.is_set():
            return None

        for (typ, tme) in command:
            if typ == 1:
                if tme > 1000:
                    binary = binary * 10 + 1
                else:
                    binary *= 10

        s = str(binary)
        if len(s) > 34:
            binary = int(s[:34])

        return binary

    @staticmethod
    def _convert_hex(binary_value):
        tmp_b2 = int(str(binary_value), 2)
        return hex(tmp_b2)

    def run(self, stop_event):
        try:
            while not stop_event.is_set():
                b = self._get_binary(stop_event)
                if b is None:
                    break

                in_data = self._convert_hex(b)
                name = self.code_to_name.get(in_data)
                if name:
                    self.on_press(name)
        finally:
            self.cleanup()

    def cleanup(self):
        try:
            GPIO.cleanup(self.pin)
        except Exception:
            pass