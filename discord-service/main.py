import asyncio
from socket import gaierror
from websockets.exceptions import ConnectionClosedError
from websockets.client import connect
from ahk import AHK
import time
import traceback

ahk = AHK()

D_X = 95
D_Y = 36

class Status:
    Unknown = -1
    Online = 0
    Away = 1
    DND = 2
    Invisible = 3

STATUSES: dict[int, int] = {
    Status.Online:     30,
    Status.Away:       -10,
    Status.DND:       -50,
    Status.Invisible: -90
}

CARDS = {
    '8a-f6-3d-98': Status.Online,
    '23-49-81-52': Status.Away,
    '3a-ff-3b-98': Status.DND,
    'fa-7f-3c-98': Status.Invisible
}

def stamp():
    return time.strftime('[%H:%M:%S]', time.localtime())

class ConnectionLogger:
    def __init__(self):
        self.last_retry_exc = None
        self.retry_count = 0
        self.last_connected_time = None

    def log_connected(self, transport):
        if self.retry_count > 0:
            print("") # newline since retry counts are with \r
        print(F"{stamp()} Connection made: {transport}", end='')
        if self.last_connected_time:
            print(F" (after {time.time() - self.last_connected_time:.0f}s)", end='')
        print("")
        self.last_retry_exc = None
        self.retry_count = 0
        self.last_connected_time = time.time()

    def log_disconnected(self, exc):
        print(F"{stamp()} Connection lost: {exc}")

    def log_retry_fail(self, exc, retry_time):
        if self.last_retry_exc != exc:
            if self.retry_count > 0:
                print("") # newline since retry counts are with \r
            print(F"{stamp()} Reconnect failed: {exc} (retry every {retry_time}s)")
            self.last_retry_exc = exc
            self.retry_count = 0
        else:
            self.retry_count += 1
            print(F"  {self.retry_count} retries failed: {exc}", end='\r')
            

async def set_status(status):
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
    
    elif status == Status.Unknown:
        print(f'Not setting unknown status')
        return

    # record user state to return to
    initPos = ahk.mouse_position
    initApp = ahk.active_window

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
        print(F"Discord window was not found.")
    else:
        discordApp.activate()
        # await asyncio.sleep(sleep_time)

        dposx, dposy, dsizx, dsizy = discordApp.rect

        # change status as appropriate:
        
        # profile and presence popup
        await q_move_mouse(D_X, 24, doClick=True)

        # move to hover over status, showing drop-down menu
        await q_move_mouse(D_X, 160, doClick=False)

        # move over the statuses to avoid closing the menu
        # (going diagonally will leave the button rect before entering the menu)
        await q_move_mouse(D_X+300, 160, doClick=False)

        # click on the status, which will also close the pop up and drop-down
        status_y = STATUSES[status]
        await q_move_mouse(D_X+300, 160+status_y, doClick=True)

        # await asyncio.sleep(2)

        #return to the original user state
        ahk.mouse_move(*initPos, speed=mouse_speed, relative=False, blocking=True)
        # ahk.mouse_position = initPos
        initApp.activate()
        
RETRY_TIME = 5

async def main():
    log = ConnectionLogger()
    while True:
        try:
            ws = await connect('ws://pincoya.lan:10022')
            log.log_connected(ws.host)

            lastStatus = Status.Unknown

            while not ws.closed:
                msg: str = await ws.recv() # type: ignore
                print(F'{stamp()} New card: {msg}')

                newstatus = CARDS.get(msg, Status.Unknown)

                if newstatus != lastStatus:
                    await set_status(newstatus)

                lastStatus = newstatus

            log.log_disconnected('closed')
        except ConnectionClosedError:
            log.log_disconnected('closed')
        except ConnectionRefusedError:
            log.log_retry_fail('refused', RETRY_TIME)
        except gaierror:
            log.log_retry_fail('no network', RETRY_TIME)
        except Exception as e:
            log.log_retry_fail(F'other: {e}', RETRY_TIME)
            traceback.print_exc()
        await asyncio.sleep(3)

asyncio.run(main())



