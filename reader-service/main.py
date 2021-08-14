import serial, asyncio
from concurrent.futures import ThreadPoolExecutor
from adafruit_pn532.uart import PN532_UART
import traceback
import board
import digitalio
from websockets.server import serve as ws_serve, WebSocketServerProtocol
from functools import partial

pool = ThreadPoolExecutor()

connections: list[WebSocketServerProtocol] = []
reader_task = None

def dout(pin):
    p = digitalio.DigitalInOut(pin)
    p.direction = digitalio.Direction.OUTPUT
    return p

status_led = dout(board.D17)
status_led.value = 0

async def blink():
    status_led.value = 1
    await asyncio.sleep(0.25)
    status_led.value = 0

async def card_read(pn532):
    #status_led.value = 1
    uid = await asyncio.get_event_loop().run_in_executor(pool, partial(pn532.read_passive_target, timeout=0.5))
    #status_led.value = 0
    return uid

async def card_read_loop():
    try:
        while True:
            try:
                uart = serial.Serial('/dev/ttyS0', baudrate=115200, timeout=1)
                pn532 = PN532_UART(uart, debug=False)
                pn532.SAM_configuration()
                while connections:
                    uid = await card_read(pn532)
                    if not uid:
                        continue
                    status_led.value = 1
                    uid_str = '-'.join(hex(i)[2:] for i in uid)
                    print(F"Card: {uid_str}")
                    for ws in list(connections):
                        await ws.send(uid_str)
                    status_led.value = 0
            except RuntimeError as e:
                uart.close()
                await asyncio.sleep(1)
                print(F"Error: {e}")
                print(traceback.format_exc().replace('\n', '\n     '))
    except (KeyboardInterrupt, asyncio.CancelledError) as e:
        # pn532.power_down()
        # uart.close()
        raise e
    finally:
        #pn532.power_down()
        uart.close()
        
async def handle_connection(ws: WebSocketServerProtocol, _path: str):
    global reader_task
    if reader_task is None or reader_task.done():
        print('New connection: Starting reading task.')
        reader_task = asyncio.create_task(card_read_loop())
    connections.append(ws)
    await ws.wait_closed()
    connections.remove(ws)
    if not connections:
        print('No more connections: Stopping reading task.')
        reader_task.cancel()



async def main():
    
    ws = await ws_serve(handle_connection, '192.168.12.247', 10022)
    print('Started server.')

    
    # 16, 19, 20, 21, 26

    # while True:
    #     led.value = not led.value
    #     await asyncio.sleep(1)

    await ws.wait_closed()

asyncio.run(main())