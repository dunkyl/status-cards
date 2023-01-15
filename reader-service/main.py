import serial, asyncio
from concurrent.futures import ThreadPoolExecutor
from adafruit_pn532.uart import PN532_UART
import traceback
import board
import digitalio
from websockets.server import serve as ws_serve, WebSocketServerProtocol
from functools import partial
import socket

import datetime

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(('8.8.8.8', 1))
local_ip = s.getsockname()[0]

pool = ThreadPoolExecutor()

connections: list[WebSocketServerProtocol] = []
reader_task = None

lights_out_range = (datetime.time(22, 0), datetime.time(6, 0))

tz = datetime.datetime.utcnow().astimezone().tzinfo

current_status = None
is_night = False
fadeoutTask = None

class Status:
    Unknown = -1
    Online = 0
    Away = 1
    DND = 2
    Invisible = 3
    Custom = 4

CARDS = {
    '8a-f6-3d-98': Status.Online,
    '23-49-81-52': Status.Away,
    '3a-ff-3b-98': Status.DND,
    'fa-7f-3c-98': Status.Invisible
}

def dout(pin, value=0):
    p = digitalio.DigitalInOut(pin)
    p.direction = digitalio.Direction.OUTPUT
    p.value = value
    return p

LEDS = {
    'g': dout(board.D6),
    'w': dout(board.D17),
    'r': dout(board.D22),
    'p': dout(board.D16),
    'b': dout(board.D12),
}
LEDS_I = list(LEDS.values())

async def clear_leds_to(x):
    for i in range(len(LEDS_I)):
        LEDS_I[i].value = 1
        await asyncio.sleep(0.25)
    for i in range(len(LEDS_I)):
        LEDS_I[i].value = x == i
        await asyncio.sleep(0.25)

async def blink():
    LEDS['w'].value = 1
    await asyncio.sleep(0.25)
    LEDS['w'].value = 0

async def lights_out_fadeout(led_i: int):
    print('starting fade out')
    await asyncio.sleep(10)
    for _ in range(10):
        LEDS_I[led_i].value = 1
        await asyncio.sleep(1)
        LEDS_I[led_i].value = 0
        await asyncio.sleep(1)
    print('fade out done')

async def lights_out_fadein(led_i: int):
    print('starting fade in')
    for _ in range(10):
        LEDS_I[led_i].value = 0
        await asyncio.sleep(1)
        LEDS_I[led_i].value = 1
        await asyncio.sleep(1)
    print('fade in done')

async def card_read(pn532):
    #status_led.value = 1
    uid = await asyncio.get_event_loop().run_in_executor(pool, partial(pn532.read_passive_target, timeout=0.5))
    #status_led.value = 0
    return uid

async def card_read_loop():
    uart = None
    global fadeoutTask
    global is_night
    global current_status
    
    try:
        while True:
            try:
                uart = serial.Serial('/dev/serial1', baudrate=115200, timeout=1)
                pn532 = PN532_UART(uart, debug=False)
                pn532.SAM_configuration()
                while connections:
                    uid = await card_read(pn532)
                    if uid:
                        
                        uid_str = '-'.join(hex(i)[2:] for i in uid)
                        print(F"Card: {uid_str}")
                        for ws in list(connections):
                            await ws.send(uid_str)
                        await blink()
                        status = CARDS.get(uid_str, None)
                        if status is not None:
                            await clear_leds_to(status)
                            current_status = status
                            is_night = False # re-do fade after status change if night
                            if fadeoutTask is not None:
                                print('canceling fadeout task, new card')
                                fadeoutTask.cancel()

                    time_now = datetime.datetime.now(tz).time()
                    # transition to night
                    if not is_night and (time_now > lights_out_range[0] or time_now < lights_out_range[1]):
                        is_night = True
                        print('is night, queueing fadeout task')
                        fadeoutTask = asyncio.create_task(
                            lights_out_fadeout(current_status if current_status is not None else 0)
                        )

                    # transition to day
                    if is_night and (time_now > lights_out_range[1] and time_now < lights_out_range[0]):
                        is_night = False
                        print('is day, queueing fadein task')
                        fadeoutTask = asyncio.create_task(
                            lights_out_fadein(current_status if current_status is not None else 0)
                        )

            except RuntimeError as e:
                if uart is not None:
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
        if uart is not None:
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
    
    ws = await ws_serve(handle_connection, local_ip, 10022)
    print('Started server.')

    
    # 16, 19, 20, 21, 26

    # while True:
    #     led.value = not led.value
    #     await asyncio.sleep(1)

    await ws.wait_closed()

asyncio.run(main())
