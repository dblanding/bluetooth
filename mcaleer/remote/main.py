# Kevin McAleer
# 2023-06-28
# Bluetooth cores specification versio 5.4 (0x0D)

import sys

import aioble
import bluetooth
import gc
import machine
import uasyncio as asyncio
from micropython import const, mem_info
from pico_lcd_1_14 import LCD_1inch14
from machine import Pin,SPI,PWM
import framebuf
import time


def uid():
    """ Return the unique id of the device as a string """
    return "{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}".format(
        *machine.unique_id())

MANUFACTURER_ID = const(0x02A29)
MODEL_NUMBER_ID = const(0x2A24)
SERIAL_NUMBER_ID = const(0x2A25)
HARDWARE_REVISION_ID = const(0x2A26)
BLE_VERSION_ID = const(0x2A28)

led = machine.Pin("LED", machine.Pin.OUT)

# Begin set up of LCD
BL = 13
DC = 8
RST = 12
MOSI = 11
SCK = 10
CS = 9

pwm = PWM(Pin(BL))
pwm.freq(1000)
pwm.duty_u16(32768)#max 65535

LCD = LCD_1inch14()
#color BRG
LCD.fill(LCD.white)

LCD.show()
LCD.text("Raspberry Pi Pico",90,40,LCD.red)
LCD.text("PicoGo",90,60,LCD.green)
LCD.text("Pico-LCD-1.14",90,80,LCD.blue)

LCD.hline(10,10,220,LCD.blue)
LCD.hline(10,125,220,LCD.blue)
LCD.vline(10,10,115,LCD.blue)
LCD.vline(230,10,115,LCD.blue)

LCD.show()

keyA = Pin(15,Pin.IN,Pin.PULL_UP)
keyB = Pin(17,Pin.IN,Pin.PULL_UP)

key2 = Pin(2 ,Pin.IN,Pin.PULL_UP)
key3 = Pin(3 ,Pin.IN,Pin.PULL_UP)
key4 = Pin(16 ,Pin.IN,Pin.PULL_UP)
key5 = Pin(18 ,Pin.IN,Pin.PULL_UP)
key6 = Pin(20 ,Pin.IN,Pin.PULL_UP)

# End of LCD setup


# _ENV_SENSE_TEMP_UUID = bluetooth.UUID(0x1800)
_GENERIC = bluetooth.UUID(0x1848)
_BUTTON_UUID = bluetooth.UUID(0x2A6E)
_ROBOT = bluetooth.UUID(0x180A)

_BLE_APPEARANCE_GENERIC_REMOTE_CONTROL = const(384)

# Advertising frequency
ADV_INTERVAL_MS = 250_000

device_info = aioble.Service(_ROBOT)

connection = None

# Create characteristics for device info
aioble.Characteristic(device_info, bluetooth.UUID(MANUFACTURER_ID), read=True, initial="KevsRobotsRemote")
aioble.Characteristic(device_info, bluetooth.UUID(MODEL_NUMBER_ID), read=True, initial="1.0")
aioble.Characteristic(device_info, bluetooth.UUID(SERIAL_NUMBER_ID), read=True, initial=uid())
aioble.Characteristic(device_info, bluetooth.UUID(HARDWARE_REVISION_ID), read=True, initial=sys.version)
aioble.Characteristic(device_info, bluetooth.UUID(BLE_VERSION_ID), read=True, initial="1.0")

remote_service = aioble.Service(_GENERIC)

button_characteristic = aioble.Characteristic(
    remote_service, _BUTTON_UUID, read=True, notify=True
)

print('registering services')
aioble.register_services(remote_service, device_info)

connected = False

async def remote_task():
    """ Send the event to the connected device """
    while True:
        if not connected:
            print('not connected')
            await asyncio.sleep_ms(1000)
            continue

        if (keyA.value() == 0):
            button_characteristic.write(b"a")
            button_characteristic.notify(connection, b"a")
            
        elif (keyB.value() == 0):
            button_characteristic.write(b"b")
            button_characteristic.notify(connection, b"b")

        elif (key2.value() == 0):
            button_characteristic.write(b"u")
            button_characteristic.notify(connection, b"u")

        elif (key3.value() == 0):
            button_characteristic.write(b"c")
            button_characteristic.notify(connection, b"c")

        elif (key4.value() == 0):
            button_characteristic.write(b"l")
            button_characteristic.notify(connection, b"l")

        elif (key5.value() == 0):
            button_characteristic.write(b"d")
            button_characteristic.notify(connection, b"d")
                
        elif (key6.value() == 0):
            button_characteristic.write(b"r")
            button_characteristic.notify(connection, b"r")

        else:
            button_characteristic.notify(connection, b"!")

        # Show button pushed on LCD
        if(keyA.value() == 0):
            LCD.fill_rect(208,12,20,20,LCD.red)
            print("A")
        else :
            LCD.fill_rect(208,12,20,20,LCD.white)
            LCD.rect(208,12,20,20,LCD.red)

        if(keyB.value() == 0):
            LCD.fill_rect(208,103,20,20,LCD.red)
            print("B")
        else :
            LCD.fill_rect(208,103,20,20,LCD.white)
            LCD.rect(208,103,20,20,LCD.red)

        if(key2.value() == 0):
            LCD.fill_rect(37,35,20,20,LCD.red)
            print("UP")
        else :
            LCD.fill_rect(37,35,20,20,LCD.white)
            LCD.rect(37,35,20,20,LCD.red)

        if(key3.value() == 0):
            LCD.fill_rect(37,60,20,20,LCD.red)
            print("CTRL")
        else :
            LCD.fill_rect(37,60,20,20,LCD.white)
            LCD.rect(37,60,20,20,LCD.red)

        if(key4.value() == 0):
            LCD.fill_rect(12,60,20,20,LCD.red)
            print("LEFT")
        else :
            LCD.fill_rect(12,60,20,20,LCD.white)
            LCD.rect(12,60,20,20,LCD.red)

        if(key5.value() == 0):
            LCD.fill_rect(37,85,20,20,LCD.red)
            print("DOWN")
        else :
            LCD.fill_rect(37,85,20,20,LCD.white)
            LCD.rect(37,85,20,20,LCD.red)

        if(key6.value() == 0):
            LCD.fill_rect(62,60,20,20,LCD.red)
            print("RIGHT")
        else :
            LCD.fill_rect(62,60,20,20,LCD.white)
            LCD.rect(62,60,20,20,LCD.red)

        LCD.show()

        await asyncio.sleep_ms(10)


# Serially wait for connections.
# Don't advertise while a central is connected
async def peripheral_task():
    print('peripheral task started')
    global connected, connection
    while True:
        connected = False
        async with await aioble.advertise(
            ADV_INTERVAL_MS, 
            name="KevsRobots", 
            appearance=_BLE_APPEARANCE_GENERIC_REMOTE_CONTROL, 
            services=[_GENERIC]
        ) as connection:
            print("Connection from", connection.device)
            connected = True
            print(f"connected: {connected}")
            await connection.disconnected(timeout_ms=None)
            print(f'disconnected')
        

async def blink_task():
    print('blink task started')
    toggle = True
    while True:
        led.value(toggle)
        toggle = not toggle
        blink = 1000
        if connected:
            blink = 1000
        else:
            blink = 250
        await asyncio.sleep_ms(blink)
        
async def main():
    tasks = [
        asyncio.create_task(peripheral_task()),
        asyncio.create_task(blink_task()),
        asyncio.create_task(remote_task()),
    ]
    await asyncio.gather(*tasks)

asyncio.run(main())
