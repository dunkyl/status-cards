import serial, asyncio
from concurrent.futures import ThreadPoolExecutor
import traceback
import board
import digitalio

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

async def blink(led='w'):
    LEDS[led].value = 1
    await asyncio.sleep(0.25)
    LEDS[led].value = 0



async def main():
    
    while True:
        for led in LEDS:
            await blink(led)
        await asyncio.sleep(0.25)
    
asyncio.run(main())
