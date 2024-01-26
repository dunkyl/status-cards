import serial
from adafruit_pn532.uart import PN532_UART

uart = serial.Serial('/dev/serial0', baudrate=115200, timeout=1)
pn532 = PN532_UART(uart, debug=False)
pn532.SAM_configuration()
try:
    while True:
        print('hi')
        if pn532.listen_for_passive_target():
            uid = pn532.read_passive_target()
            print(uid)
finally:
    pn532.power_down()
    uart.close()