import serial, asyncio
from concurrent.futures import ThreadPoolExecutor
from adafruit_pn532.uart import PN532_UART
from websockets.server import serve as ws_serve, WebSocketServerProtocol

pool = ThreadPoolExecutor()

loop = asyncio.get_event_loop()

connections: list[WebSocketServerProtocol] = []
reader_task = None

async def card_read(pn532):
    return await loop.run_in_executor(pool, pn532.read_passive_target)

async def card_read_loop():
    try:
        uart = serial.Serial('/dev/ttyS0', baudrate=115200, timeout=10)
        pn532 = PN532_UART(uart, debug=False)
        pn532.SAM_configuration()
        while connections:
            uid = await card_read(pn532)
            if not uid:
                continue
            uid_str = '-'.join(hex(i) for i in uid)
            print(F"Card: {uid_str}")
            for ws in list(connections):
                ws.send(uid_str)
    except (KeyboardInterrupt, asyncio.CancelledError) as e:
        pn532.power_down()
        uart.close()
        raise e
        
async def handle_connection(ws: WebSocketServerProtocol):
    global reader_task
    if reader_task is None:
        print('New connection: Starting reading task.')
        reader_task = asyncio.create_task(card_read_loop())
    connections.append(ws)
    await ws.wait_closed()
    connections.remove(ws)
    if not connections:
        print('No more connections: Stopping reading task.')
        reader_task.cancel()

async def main():
    
    ws = await ws_serve(handle_connection, 'octopi', 10022)
    print('Started server.')
    await ws.wait_closed()