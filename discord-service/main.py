import asyncio
from websockets.client import connect, WebSocketClientProtocol
from ahk import AHK

ahk = AHK()

UPDATE_YOFF = 30 # -20

x = 90
class Status:
    Unknown = -1
    Online = 0
    Away = 1
    DND = 2
    Invisible = 3

STATUSES: dict[int, tuple[int, int]] = {
    Status.Online:    (x, 451),
    Status.Away:      (x, 483),
    Status.DND:       (x, 518),
    Status.Invisible: (x, 576)
}

CARDS = {
    '3a-ff-3b-98': Status.Online,
    '23-49-81-52': Status.Invisible
}

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

    # go to discord
    discordApp = ahk.find_window(title=dTitle)
    discordApp.activate()
    await asyncio.sleep(0.1)

    dposx, dposy, dsizx, dsizy = discordApp.rect

    dsizy += UPDATE_YOFF

    # change status as appropriate
    ahk.mouse_move(x, 892-920+dsizy-UPDATE_YOFF, speed=2, relative=False, mode='Window', blocking=True)
    await asyncio.sleep(0.1)
    ahk.click()
    await asyncio.sleep(0.2)
    ahk.mouse_move( *(STATUSES[status]), speed=2, relative=False, mode='Window', blocking=True)
    await asyncio.sleep(0.2)
    ahk.click()

    #return to the original user state
    ahk.mouse_move(*initPos, speed=2, relative=False, blocking=True)
    # ahk.mouse_position = initPos
    initApp.activate()
        

async def main():
    ws = await connect('ws://192.168.12.247:10022')
    print('connected')

    isFirstChange = True
    lastStatus = Status.Unknown

    while not ws.closed:
        msg = await ws.recv()
        print(F'New card: {msg}')

        newstatus = CARDS.get(msg, Status.Unknown)

        if isFirstChange:
            pass
            isFirstChange = False
        elif newstatus != lastStatus:
            await set_status(newstatus)

        lastStatus = newstatus

    print('disconnected')

asyncio.run(main())



