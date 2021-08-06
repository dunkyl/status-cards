import busio, board
from adafruit_pn532.uart import PN532_UART

pn532 = PN532_UART(busio.UART(board.TXD, board.RXD))

pn532.SAM_configuration()

while True:
    uid = pn532.read_passive_target()
    print('.', end="", flush=True)
    if uid is None:
        continue
    print('Found card with UID:', '-'.join([hex(i) for i in uid]))