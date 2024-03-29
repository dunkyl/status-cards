'Listens to the reader service and updates the discord status accordingly.'
from datetime import datetime
import asyncio

from ahk import AHK
import bedtime

from common import *

def stamp(): return datetime.now().strftime('[%H:%M:%S]')

def humanize_time(seconds: float) -> str:
    s = seconds % 60
    m = (seconds // 60) % 60
    h = seconds // 3600
    text = ""
    if h > 0:
        text += F"{h:.0f}h "
    if m > 0:
        text += F"{m:.0f}m "
    if s > 0 or not text:
        text += F"{s:.1f}s"
    return text

class ConnectionLogger:
    def __init__(self):
        self.last_retry_exc = None
        self.retry_count = 0
        self.last_connected_time = None
        self.just_slept = False
        self.retry_time = 5

    def log_connected(self, transport):
        if self.retry_count > 0:
            print("") # newline since retry counts are with \r
        print(F"{stamp()} Connection made: {transport}", end='')
        if self.last_connected_time:
            elapsed = (datetime.now() - self.last_connected_time).total_seconds()
            print(F" (after {humanize_time(elapsed)})", end='')
        print("")
        self.last_retry_exc = None
        self.retry_count = 0
        self.just_slept = False
        self.last_connected_time = datetime.now()

    def log_disconnected(self, exc: str=""):
        if not self.just_slept:
            self.last_connected_time = datetime.now()
            print(F"{stamp()} Connection lost: {exc}")

    def log_slept(self):
        self.last_connected_time = datetime.now()
        print(F"{stamp()} Sleeping")
        self.just_slept = True

    def log_connect_fail(self, exc):
        if self.last_retry_exc != exc:
            if self.retry_count > 0:
                print("") # newline since retry counts are with \r
            print(F"{stamp()} Reconnect failed: {exc} (retry every {self.retry_time}s)")
            self.last_retry_exc = exc
            self.retry_count = 0
        else:
            self.retry_count += 1
            print(F"  {self.retry_count} retries failed: {exc}", end='\r')

ahk = AHK()

async def set_status(status: 'str|None'):
    # find the discord application
    apps = list(ahk.windows())
    dTitle = None
    for app in apps:
        if 'Discord' in str(app.title):
            dTitle = app.title
            break

    if dTitle is None:
        print(f'Discord not found, but got state {status} anyway.')
        return
    
    elif status is None:
        print('Not setting unknown status')
        return

    # record user state to return to
    initPos = ahk.mouse_position
    initApp = ahk.active_window
    if initApp is None:
        raise RuntimeError("Active window not found")

    sleep_time = 0.05
    mouse_speed = 2
    async def q_move_mouse(x, y, doClick):
        await asyncio.sleep(sleep_time)
        ahk.mouse_move(x, dsizy-y, speed=mouse_speed, relative=False, mode='Window', blocking=True)
        if doClick:
            ahk.click()
            await asyncio.sleep(sleep_time)

    # go to discord
    discordApp = ahk.find_window(title=dTitle)
    if discordApp is None:
        print("Discord window was not found.")
    else:
        discordApp.activate()
        # await asyncio.sleep(sleep_time)

        dposx, dposy, dsizx, dsizy = discordApp.rect

        # change status as appropriate:
        D_X = 95
        D_Y = 185
        
        # profile and presence popup
        await q_move_mouse(D_X, 24, doClick=True)

        # move to hover over status, showing drop-down menu
        await q_move_mouse(D_X, D_Y, doClick=False)

        # move over the statuses to avoid closing the menu
        # (going diagonally will leave the button rect before entering the menu)
        await q_move_mouse(D_X+300, D_Y, doClick=False)

        # click on the status, which will also close the pop up and drop-down
        status_y = {
            Status.Online:      -5,
            Status.Away:       -40,
            Status.Dnd:        -70,
            Status.Invisible: -110
        }[status]
        await q_move_mouse(D_X+300, D_Y+status_y, doClick=True)

        # await asyncio.sleep(2)

        #return to the original user state
        ahk.mouse_move(*initPos, speed=mouse_speed, relative=False, blocking=True)
        # ahk.mouse_position = initPos
        initApp.activate()

log = ConnectionLogger()
ws = None
def on_sleep():
    global ws
    if ws is not None:
        ws.fail_connection(reason="Sleeping")
        ws = None
    log.log_slept()

sleepListen = bedtime.Listener(on_sleep = on_sleep)

from websockets.exceptions import ConnectionClosed
from socket import gaierror
from websockets.client import connect
import traceback

async def main():
    global ws

    while True:
        try:
            try:
                ws = await connect(config['discord_side']['reader_address'])
            except ConnectionRefusedError:
                log.log_connect_fail('refused')
                continue
            except gaierror:
                log.log_connect_fail('no network')
                continue
            finally:
                await asyncio.sleep(1)
            log.log_connected(ws.host)

            lastStatus = None

            while ws.open:
                msg: str = await ws.recv() # type: ignore
                print(F'{stamp()} New card: {msg}')

                newstatus = card_to_status(msg)

                if newstatus != lastStatus:
                    await set_status(newstatus)

                lastStatus = newstatus
        except (ConnectionClosed, TimeoutError):
            log.log_disconnected('closed')
        except (OSError) as e:
            if e.errno == 121:
                # sometimes thrown when a underlying websocket thread is interrupted by sleep
                log.log_disconnected('closed')
            else:
                log.log_disconnected(F'other: {e}')
                traceback.print_exc()
        except Exception as e:
            log.log_connect_fail(F'other: {e}')
            traceback.print_exc()
        ws = None
        await asyncio.sleep(5)

asyncio.run(main())