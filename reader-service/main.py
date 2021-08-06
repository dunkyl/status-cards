import serial, board
from adafruit_pn532.uart import PN532_UART

pn532 = PN532_UART(serial.Serial('/dev/ttyS0', baudrate=115200, timeout=100))

pn532.SAM_configuration()

while True:
    uid = pn532.read_passive_target(timeout=0.5)
    print('.', end="")
    if uid is None:
        continue
    print('Found card with UID:', '-'.join([hex(i) for i in uid]))