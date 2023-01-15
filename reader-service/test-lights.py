import asyncio
import board
import digitalio

def dout(pin, value=0):
    p = digitalio.DigitalInOut(pin)
    p.direction = digitalio.Direction.OUTPUT
    p.value = value
    return p

LEDS = [
    dout(board.D6),
    dout(board.D17),
    dout(board.D22),
    dout(board.D16),
    dout(board.D12),
]

async def blink(led):
    led.value = 1
    await asyncio.sleep(0.25)
    led.value = 0
    await asyncio.sleep(0.25)

async def main():
    
    while True:
        for led in LEDS:
            await blink(led)
    
asyncio.run(main())
