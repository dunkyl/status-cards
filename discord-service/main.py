import sys

from ahk import AHK
import serial
import serial.tools.list_ports
from time import sleep

ahk = AHK()

LAST_STATE = -1

UPDATE_YOFF = 30 # -20

portInfos = serial.tools.list_ports.comports()

ARDUINO_UNO = (9025, 67)

for portInfo in portInfos:
    if (portInfo.vid, portInfo.pid) == ARDUINO_UNO:
        print(F"Arduino Uno found on {portInfo.name}.\nDevice: {portInfo.description}\nS/N: {portInfo.serial_number}")
        comPort = portInfo.device
        break
else:
    print("No Arduino Uno found!\nExisting COM ports:")
    for portInfo in portInfos:
        print(portInfo.__dict__)
    input("\n\n------\nPress any key to exit.")
    sys.exit(0)

dcStateIndex = 0
stateIndex = 3
resumed = True

charge = 2
charging = False

didFirstState = False

class Status:
    Online = 0
    Away = 1
    DND = 2
    Invisible = 3

x = 90

STATUSES: dict[int, tuple[int, int]] = {
    Status.Online:    (x, 451),
    Status.Away:      (x, 483),
    Status.DND:       (x, 518),
    Status.Invisible: (x, 576)
}

lastChangedToState = -1

while True:

    try:

        with serial.Serial(comPort, 9600, timeout=10) as dev:

            while True:
                try:
                    stateB = dev.readline()
                    if charging:
                        # print(charge)
                        charge += 1
                    if stateB == b'':
                        continue
                    stateIndex = int(stateB) # (not) block until state update
                except ValueError:
                    print(f'Unrecognized: {stateB}')
                    sleep(10)
                    continue

                except TimeoutError:
                    continue

                if not stateIndex == LAST_STATE:
                    charging = True
                    
                if charging and charge == 30:
                    charging = False
                    charge = 0

                    if stateIndex == dcStateIndex and not resumed:
                        print(f'New state: {stateIndex}. Resuming...')
                        resumed = True
                        continue
                    if not resumed:
                        print(f'New state: {stateIndex}. Deferring until resume...')
                        continue
                    LAST_STATE = stateIndex

                    if not stateIndex == lastChangedToState:

                        print(f'New state: {stateIndex}.')
                        lastChangedToState = stateIndex

                        # find the discord application
                        apps = list(ahk.windows())
                        dTitle = None
                        for app in apps:
                            if 'Discord' in str(app.title):
                                dTitle = app.title
                                break

                        if not didFirstState:
                            didFirstState = True
                            print("Deferring first state change!")
                            continue
                        
                        if dTitle is not None:
                            #print(dTitle)
                            # record user state to return to
                            initPos = ahk.mouse_position
                            initApp = ahk.active_window

                            # go to discord
                            discordApp = ahk.find_window(title=dTitle)
                            discordApp.activate()
                            sleep(0.1)

                            dposx, dposy, dsizx, dsizy = discordApp.rect

                            dsizy += UPDATE_YOFF

                            STATUSESREAL = {key: (dx, dy) for key, (dx, dy) in STATUSES.items()}

                            # change status as appropriate
                            ahk.mouse_move(x, 892-920+dsizy-UPDATE_YOFF, speed=2, relative=False, mode='Window', blocking=True)
                            sleep(0.1)
                            ahk.click()
                            sleep(0.2)
                            ahk.mouse_move( *(STATUSESREAL[stateIndex]), speed=2, relative=False, mode='Window', blocking=True)
                            sleep(0.2)
                            ahk.click()

                            #return to the original user state
                            ahk.mouse_move(*initPos, speed=2, relative=False, blocking=True)
                            # ahk.mouse_position = initPos
                            initApp.activate()

                        else: # discord wasn't open?
                            print(f'Discord not found, but got state {stateIndex} anyway.')
    except serial.serialutil.SerialException as e:
        print('dc\'d')
        resumed = False
        dcStateIndex = stateIndex
        pass
    sleep(10)



