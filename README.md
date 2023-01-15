# Discord Status Cards

NFC cards that control your Discord status.

Expects a [PN532 NFC reader](https://www.adafruit.com/product/364) on a microcrontroller, probably a raspberry pi. Tested on a Raspberry Pi Zero W. It connects to a Windows PC via WiFi and uses AHK to change the status.

Requirements, card reader device:
 - Python 3.11+
 - Adafruit Python compatible GPIO and UART
 - Above mentioned PN532 reader
 - Some network connection, on the same LAN as the PC

Recommendations:
 - LEDs to indicate current status

Requirements, Windows PC:
 - Python 3.11+
 - [Discord app](https://discord.com/download)
 - [AutoHotkey](https://www.autohotkey.com/)


## Setup

### Card reader device
Wire the PN532 to the GPIO pins of the microcontroller. See [Adafruit's guide](https://learn.adafruit.com/adafruit-nfc-rfid-on-raspberry-pi) for more information.

Install any LEDs and note the GPIO pins they are connected to.

TODO: Finish instructions

Run the reader side program:
```sh
py -3.11 reader.py
```
You may want to run this in a screen or tmux session, or add it as a service.

### Windows device
Run Discord.

Run the Discord side program:
```sh
py -3.11 discord.py
```
Leave it open, it will run in the background and retry connections automatically.