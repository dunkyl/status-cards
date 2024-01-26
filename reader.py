from websockets import ConnectionClosed
import serial, asyncio
from concurrent.futures import ThreadPoolExecutor
from adafruit_pn532.uart import PN532_UART
import traceback
import board
import digitalio
from websockets.server import serve as ws_serve, WebSocketServerProtocol
from functools import partial
# import socket

from common import *

import datetime

# s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# s.connect(('8.8.8.8', 1))
# local_ip = s.getsockname()[0]

pool = ThreadPoolExecutor()

connections: list[WebSocketServerProtocol] = []
reader_task = None

lights_on_range = (
    datetime.time(config['reader_side']['night_end_hour'], 0),
    datetime.time(config['reader_side']['night_start_hour'], 0))

tz = datetime.datetime.utcnow().astimezone().tzinfo

def digital_out(pin: str, value=False):
    p = digitalio.DigitalInOut(getattr(board, pin))
    p.switch_to_output(value)
    return p

# { status : DigitalInOut pin }
leds = { k: digital_out(v) for k, v in config['reader_side']['pins'].items() }

async def clear_leds_to(new_status: str):
    for status in config['cards'].values():
        leds[status].value = 1
        await asyncio.sleep(0.25)
    for status in config['cards'].values():
        leds[status].value = new_status == status
        await asyncio.sleep(0.25)

async def blink_white():
    leds['Invisible'].value = 1
    await asyncio.sleep(0.25)
    leds['Invisible'].value = 0

async def lights_out_fade(status: str, fade_in: bool = False):
    print('starting fade out')
    await asyncio.sleep(10)
    for _ in range(10):
        leds[status].value = not fade_in
        await asyncio.sleep(1)
        leds[status].value = fade_in
        await asyncio.sleep(1)
    print('fade out done')

async def card_read(pn532: PN532_UART):
    uid = await asyncio.get_event_loop().run_in_executor(pool, 
        partial(pn532.read_passive_target, timeout=1)) # seconds
    # TODO: above timeout seems to support floats in implementation
    return uid


current_status = None
is_night = False
fadeoutTask = None

async def on_card_read(uid: 'list[int] | None'):
    if not uid: return
    global is_night
    global current_status
    uid_str = '-'.join(hex(i)[2:] for i in uid)
    print(F"Card: {uid_str}")
    for ws in list(connections):
        await ws.send(uid_str)
    await blink_white()
    status = status_to_card(uid_str)
    if status is not None:
        await clear_leds_to(status)
        current_status = status
        is_night = False # re-do fade after status change if night
        if fadeoutTask is not None:
            print('canceling fadeout task, new card')
            fadeoutTask.cancel()

def is_inside_range(time: datetime.time, range: tuple[datetime.time, datetime.time]):
    return range[0] < time < range[1]

async def card_read_loop():
    global fadeoutTask
    global is_night
    global current_status

    uart = None
    pn532 = None
    
    try:
        while True:
            try:
                uart = serial.Serial('/dev/serial0', baudrate=115200, timeout=1)
                pn532 = PN532_UART(uart, debug=False)
                pn532.SAM_configuration()
                while connections:
                    uid = await card_read(pn532)
                    
                    await on_card_read(uid)

                    time_now = datetime.datetime.now(tz).time()
                    # transition to night
                    if not is_night and not is_inside_range(time_now, lights_on_range):
                        is_night = True
                        print('is night, queueing fadeout task')
                        fadeoutTask = asyncio.create_task(
                            lights_out_fade(current_status or 'Invisible', fade_in=False)
                        )

                    # transition to day
                    if is_night and is_inside_range(time_now, lights_on_range):
                        is_night = False
                        print('is day, queueing fadein task')
                        fadeoutTask = asyncio.create_task(
                            lights_out_fade(current_status or 'Invisible', fade_in=True)
                        )

            except RuntimeError as e:
                if uart is not None:
                    uart.close()
                await asyncio.sleep(1)
                print(F"Error: {e}")
                print(traceback.format_exc().replace('\n', '\n     '))
    finally:
        if pn532 is not None:
            pn532.power_down()
        if uart is not None:
            uart.close()
        
async def handle_connection(ws: WebSocketServerProtocol, _path: str):
    global reader_task
    print(F'New connection: {ws.remote_address}')
    if reader_task is None or reader_task.done():
        print(' ... Starting reading task.')
        reader_task = asyncio.create_task(card_read_loop())
    connections.append(ws)
    while not ws.closed:
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=1)
            if msg == "how":
                await ws.send("|".join([
                    "ok",
                    current_status or "Invisible",
                    str(len(connections))
                ]))
        except asyncio.TimeoutError:
            continue
        except ConnectionClosed:
            break
    connections.remove(ws)
    print(F'Lost connected client: {ws.remote_address}')
    if not connections:
        print('No more connections: Stopping reading task.')
        reader_task.cancel()

async def main():
    
    ws = await ws_serve(
        handle_connection, '0.0.0.0', config['reader_side']['port'])
    print('Started server.')

    await ws.wait_closed()

asyncio.run(main())
