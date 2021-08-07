import asyncio
from re import S
from websockets.client import connect, WebSocketClientProtocol
from ahk import AHK

ahk = AHK()

D_X = 95
STATUS_BTN = (D_X, 24)

class Status:
    Unknown = -1
    Online = 0
    Away = 1
    DND = 2
    Invisible = 3
    Custom = 4

STATUSES: dict[int, tuple[int, int]] = {
    Status.Online:    (D_X, 281),
    Status.Away:      (D_X, 253),
    Status.DND:       (D_X, 222),
    Status.Invisible: (D_X, 160),
    Status.Custom:    (D_X, 74)
}

CARDS = {
    '8a-f6-3d-98': Status.Online,
    '23-49-81-52': Status.Away,
    '3a-ff-3b-98': Status.DND,
    'fa-7f-3c-98': Status.Invisible
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

    # change status as appropriate
    x, y = STATUS_BTN
    ahk.mouse_move(x, dsizy-y, speed=2, relative=False, mode='Window', blocking=True)
    await asyncio.sleep(0.1)
    ahk.click()
    await asyncio.sleep(0.2)
    x, y = STATUSES[status]
    ahk.mouse_move(x, dsizy-y, speed=2, relative=False, mode='Window', blocking=True)
    await asyncio.sleep(0.2)
    ahk.click()

    #return to the original user state
    ahk.mouse_move(*initPos, speed=2, relative=False, blocking=True)
    # ahk.mouse_position = initPos
    initApp.activate()
        

async def main():
    ws = await connect('ws://192.168.12.247:10022')
    print('connected')

    lastStatus = Status.Unknown

    while not ws.closed:
        msg = await ws.recv()
        print(F'New card: {msg}')

        newstatus = CARDS.get(msg, Status.Unknown)

        if newstatus != lastStatus:
            await set_status(newstatus)

        lastStatus = newstatus

    print('disconnected')

asyncio.run(main())



