"""Module to test if the RTCs have the correct time set for the given set
of ARIMU devices.

Author: Sivakumar Balasubramanian
Email: siva82kb@gmail.com
Date: 05 Dec 2022
"""

import serial
import enum
import os
import sys
import time
import struct
from datetime import datetime as dt
import asyncio
from serial.tools.list_ports import comports

from asyncarimu import ArimuAsync
from asyncarimu import ArimuCommands


async def test():
    arimu1 = ArimuAsync("COM15", 115200)
    arimu2 = ArimuAsync("COM16", 115200)
    arimu3 = ArimuAsync("COM19", 115200)
    await asyncio.sleep(2)
    # Set the device in the streaming mode.
    while True:
        try:
            _now1 = dt.now()
            _data1 = await arimu1.gettime()
            _now2 = dt.now()
            _data2 = await arimu2.gettime()
            _now3 = dt.now()
            _data3 = await arimu3.gettime()
            os.system('cls')
            sys.stdout.write("\nCOM18 [" + _now1.strftime('%H:%M:%S.%f') + f"] {_data1[3][0].strftime('%H:%M:%S.%f')} : ")
            _del1 = ((_now1 - _data1[3][0])
                    if _now1 > _data1[3][0]
                    else (_data1[3][0] - _now1))
            sys.stdout.write(f"{_del1}")
            sys.stdout.write("\nCOM19 [" + _now2.strftime('%H:%M:%S.%f') + f"] {_data2[3][0].strftime('%H:%M:%S.%f')} : ")
            _del2 = ((_now2 - _data2[3][0])
                    if _now2 > _data2[3][0]
                    else (_data2[3][0] - _now2))
            sys.stdout.write(f"{_del2}")
            sys.stdout.write("\nCOM20 [" + _now2.strftime('%H:%M:%S.%f') + f"] {_data3[3][0].strftime('%H:%M:%S.%f')} : ")
            _del3 = ((_now3 - _data3[3][0])
                    if _now3 > _data3[3][0]
                    else (_data3[3][0] - _now3))
            sys.stdout.write(f"{_del3} \n")
            sys.stdout.flush()
        except:
            pass
        await asyncio.sleep(0.1)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    tasks = [
        loop.create_task(test()),
    ]
    loop.run_until_complete(asyncio.wait(tasks))
    loop.close()