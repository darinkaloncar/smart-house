from datetime import datetime
import time


def getBinary(GPIO, pin, stop_event):
    num1s = 0
    binary = 1
    command = []
    previousValue = 0
    value = GPIO.input(pin)

    # Wait for pin low (start), but allow stopping
    while value and not stop_event.is_set():
        time.sleep(0.0001)
        value = GPIO.input(pin)

    if stop_event.is_set():
        return None

    startTime = datetime.now()

    while not stop_event.is_set():
        if previousValue != value:
            now = datetime.now()
            pulseTime = now - startTime
            startTime = now
            command.append((previousValue, pulseTime.microseconds))

        if value:
            num1s += 1
        else:
            num1s = 0

        if num1s > 10000:
            break

        previousValue = value
        value = GPIO.input(pin)

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


def convertHex(binaryValue):
    tmpB2 = int(str(binaryValue), 2)
    return hex(tmpB2)


def run_ir_loop(settings, callback, stop_event):
    import RPi.GPIO as GPIO

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    pin = int(settings.get("pin", 17))
    GPIO.setup(pin, GPIO.IN)

    Buttons = [
        0x300ff22dd, 0x300ffc23d, 0x300ff629d, 0x300ffa857, 0x300ff9867,
        0x300ffb04f, 0x300ff6897, 0x300ff02fd, 0x300ff30cf, 0x300ff18e7,
        0x300ff7a85, 0x300ff10ef, 0x300ff38c7, 0x300ff5aa5, 0x300ff42bd,
        0x300ff4ab5, 0x300ff52ad
    ]
    ButtonsNames = [
        "LEFT", "RIGHT", "UP", "DOWN", "2", "3", "1", "OK", "4", "5",
        "6", "7", "8", "9", "*", "0", "#"
    ]

    code_to_name = {hex(Buttons[i]): ButtonsNames[i] for i in range(len(ButtonsNames))}

    try:
        while not stop_event.is_set():
            b = getBinary(GPIO, pin, stop_event)
            if b is None:
                break

            inData = convertHex(b)
            name = code_to_name.get(inData)
            if name:
                print(name)
                callback(name, settings)
    finally:
        GPIO.cleanup()
