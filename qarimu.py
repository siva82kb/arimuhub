"""Module to connect to BioRehab Group's OLA based arm-use IMU bands to PyQt
applications.

Author: Sivakumar Balasubramanian
Date: 06 July 2022
email: siva82kb@gmail.com
"""

import asyncio
import time
import json
import struct
from datetime import datetime
import numpy as np
from dataclasses import dataclass
import sys
from typing import Dict

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import qasync
import attrdict 

from bleak import BleakClient
from bleak import discover
from bleak.backends.device import BLEDevice
import logging
import logging.config
log = logging.getLogger(__name__)

# These values have been randomly generated - they must match between the Central and Peripheral devices
# Any changes you make here must be suitably made in the Arduino program as well
IMU_UUID = '13012F01-F8C3-4F4A-A8F4-15CD926DA146'  #data streaming
COM_UUID = '7B85CD52-6F02-4933-816C-375FB8091A2D'  #two way transfer

# Commands defined on the IMU watch
PING = 1
LISTFILES = 2
SENDFILE = 3
DELETEFILE = 4
TERMINATE = 5
SETTIME = 6
STREAMDATA = 7
STOPSTREAM = 8


def get_timestamp(received_bytes):
    ts = [struct.unpack('<L', received_bytes[4 * i:4 * (i + 1)])[-1]
          for i in range(7)]
    timestring = f'{ts[0]}-{ts[1]}-{ts[2]}T{ts[3]}:{ts[4]}:{ts[5]}.{ts[6]}'
    return datetime.strptime(timestring, '%y-%m-%dT%H:%M:%S.%f')


class QARIMUCLient(QObject):
    
    new_data = pyqtSignal(bool)
    
    def __init__(self, devname, addr) -> None:
        super().__init__()
        self._client = None
        self._devname = devname
        self._addr = addr
        self._connected = False
        self._running = False
        self._stop = None
        self._delayms = []
        self.packetsize = 22
        self.payloadsize = 10
        self._cmd = None
        self._cmd_params = None
        self._cmd_hndlr = {PING: self._ping_hndlr,
                           LISTFILES: self._LISTFILES_hndlr,
                           SENDFILE: self._SENDFILE_hndlr,
                           DELETEFILE: self._DELETEFILE_hndlr,
                           TERMINATE: self._TERMINATE_hndlr,
                           SETTIME: self._SETTIME_hndlr,
                           STREAMDATA: self._STREAMDATA_hndlr,
                           STOPSTREAM: self._STOPSTREAM_hndlr,}
        
        # Init current data
        self.init_data()
        
        # Data logging variables
        self.datalog = attrdict.AttrDict()
        self.datalog.fhdata = None
        self.datalog.filename = None

    @property
    # def client(self) -> BleakClient:
    #     return BleakClient(self._addr)
    
    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def data(self) -> Dict:
        return self._data

    @property
    def running(self) -> bool:
        return self._running

    @property
    def devname(self):
        return self._devname

    @property
    def address(self):
        return self._addr

    @property
    def devname(self):
        return self._devname
    
    @property
    def delayms(self):
        return self._delayms
    
    @property
    def filename(self):
        return self.datalog.filename
    
    @filename.setter
    def filename(self, value):
        if self.datalog.filename != value:
            # Check if there is already a valid filename.
            if self.datalog.filename is not None:
                log.info(self.get_log_msg(f"Closing {self.datalog.filename}-data.csv"))
                self.datalog.filename = None
                self.datalog.fhdata.close()
            self.datalog.filename = value
            self.datalog.fhdata = None
            if self.datalog.filename is not None:
                log.info(self.get_log_msg(f"Opening {self.datalog.filename}-data.csv"))
                self.datalog.fhdata = open(f"{self.datalog.filename}-data.csv",
                                           "w")
                self.datalog.fhdata.write("t,devt,ax,ay,az,gx,gy,gz,sample\n")
                # Write the params file.
                self.write_params_file()
    
    def init_data(self):
        self._data = attrdict.AttrDict()
        self._data.time = 0.0
        self._data.ax = 0
        self._data.ay = 0
        self._data.az = 0
        self._data.gx = 0
        self._data.gy = 0
        self._data.gz = 0
        self._data.sample = 0

    def write_params_file(self):
        with open(f"{self.datalog.filename}-params.json", "w") as fh:
            json.dump(self._delayms, fh, indent=4)

    def get_log_msg(self, info):
        return f'[{self._devname}] {info}'
 
    async def connect(self):
        if self._connected:
            return

        async with BleakClient(self._addr) as self._client:
            self._connected = True
            log.info(self.get_log_msg(f'Connected to {self._devname} @ {self._addr}.'))
            
            # Set time
            await self.set_time()
            
            # Just wait now and execute commands that are sent it.
            while self._running:
                # Check if any commands have been set.
                if self._cmd is not None:
                    
            # Send command to start stream.
            # log.info(self.get_log_msg(f'Starting stream.'))
            # await self._client.start_notify(IMU_UUID, self._handle_newdata)
            # await self._client.write_gatt_char(COM_UUID, bytes([STREAMDATA]))
            self._running = True
            self._stop = asyncio.Event()

            # Wait till stream is stopped
            await self._stop.wait()
            self._connected = False
            self._running = False
        
        # Clear client.
        self._client = None
        
        # Stop logging if we were
        self.datalog.filename = None
                
    
    # async def start_stream(self) -> None:
    #     if self._connected:
    #         return

    #     async with BleakClient(self._addr) as self._client:
    #         self._connected = True
    #         log.info(self.get_log_msg(f'Connected to {self._devname} @ {self._addr}.'))
            
    #         # Set time
    #         await self.set_time()
            
    #         # Send command to start stream.
    #         # log.info(self.get_log_msg(f'Starting stream.'))
    #         # await self._client.start_notify(IMU_UUID, self._handle_newdata)
    #         # await self._client.write_gatt_char(COM_UUID, bytes([STREAMDATA]))
    #         self._running = True
    #         self._stop = asyncio.Event()

    #         # Wait till stream is stopped
    #         await self._stop.wait()
    #         self._connected = False
    #         self._running = False
        
    #     # Clear client.
    #     self._client = None
        
    #     # Stop logging if we were
    #     self.datalog.filename = None

    # async def stop_stream(self) -> None:
    #     if self._running:
    #         # Stop notification
    #         await self._client.write_gatt_char(COM_UUID, bytes([STOPSTREAM]))
    #         self._stop.set()
    
    async def ping(self):
        async with BleakClient(self._addr) as self._client:
            await self._client.write_gatt_char(COM_UUID, bytes([PING]))
            timestamp = get_timestamp(await self._client.read_gatt_char(COM_UUID))
        return timestamp

    async def set_time(self, estdelay=False):
        async with BleakClient(self._addr) as self._client:
            dt = datetime.now()
            unix = ",".join((f"{int(dt.microsecond / 10000)}",
                            f"{dt.second}",
                            f"{dt.minute}",
                            f"{dt.hour}",
                            f"{dt.day}",
                            f"{dt.month}",
                            f"{dt.year % 100}"))
            await self._client.write_gatt_char(COM_UUID, bytes([SETTIME]) + 
                                              bytearray(unix.encode()))
            log.info(self.get_log_msg(f"Setting time to {unix}"))
        if estdelay:
            # Get an estimate of the delay.
            _resp = await self.get_delay()
            return dt, _resp[-1]
        return dt, None
    
    async def get_delay(self, N=1):
        # Add a new instance of delay measurement.
        log.info(self.get_log_msg(f"Estimating delay."))
        async with BleakClient(self._addr) as self._client:
            i = 0
            _delay = [datetime.now().strftime("%Y/%m/%d %H:%M:%S"), []]
            while i < N:
                # Ping to get current time
                await self._client.write_gatt_char(COM_UUID, bytes([PING]))
                timestamp = get_timestamp(await self._client.read_gatt_char(COM_UUID))
                currdelay = (datetime.now() - timestamp).total_seconds() * 1000
                if currdelay > 0:
                    _delay[-1].append(currdelay)
                    i += 1
            self._delayms.append(_delay)
        log.info(self.get_log_msg(f"Avg. Delay (ms): {np.mean(self._delayms[-1][-1])}"))
        return self._delayms[-1]

    async def get_files(self):
        async with BleakClient(self._addr) as self._client:
            await self._client.write_gatt_char(COM_UUID, bytes([LISTFILES]))
            _files = bytes(await self._client.read_gatt_char(COM_UUID))
        return str(_files).split(",")

    # def _handle_newdata(self, _:int, data: bytearray):
    #     for i in range(self.payloadsize):
    #         # elapsed = (datetime.now() - self.start).total_seconds()
    #         self._data.time = struct.unpack('<d', bytes(data[(i*self.packetsize) + 0:(i*self.packetsize) + 8]))[-1]
    #         self._data.ax = struct.unpack('<h', bytes(data[(i*self.packetsize) + 8:(i*self.packetsize) + 10]))[-1]
    #         self._data.ay = struct.unpack('<h', bytes(data[(i*self.packetsize) + 10:(i*self.packetsize) + 12]))[-1]
    #         self._data.az = struct.unpack('<h', bytes(data[(i*self.packetsize) + 12:(i*self.packetsize) + 14]))[-1]
    #         self._data.gx = struct.unpack('<h', bytes(data[(i*self.packetsize) + 14:(i*self.packetsize) + 16]))[-1]
    #         self._data.gy = struct.unpack('<h', bytes(data[(i*self.packetsize) + 16:(i*self.packetsize) + 18]))[-1]
    #         self._data.gz = struct.unpack('<h', bytes(data[(i*self.packetsize) + 18:(i*self.packetsize) + 20]))[-1]
    #         self._data.sample = struct.unpack('<h', bytes(data[(i*self.packetsize) + 20:(i*self.packetsize) + 22]))[-1]
            
    #         # Log data.
    #         if self.datalog.filename != None:
    #             self._write_row()
        
    #     # Inform about new data
    #     self.new_data.emit(True)
    
    # def _write_row(self):
    #     _str = (f"{time.time():3.8f}, " +
    #             f"{self.data['time']:3.8f}, " +
    #             f"{self.data['ax']}, " +
    #             f"{self.data['ay']}, " +
    #             f"{self.data['az']}, " +
    #             f"{self.data['gx']}, " +
    #             f"{self.data['gy']}, " +
    #             f"{self.data['gz']}, " +
    #             f"{self.data['sample']}\n")
    #     self.datalog.fhdata.write(_str)


async def find_devices(names):
    """Returns the addresses of the devices that are found.
    """
    addresses = {}
    devices = await discover()
    for d in devices:
         if d.name in names:
            addresses[d.name] = d.address
    log.info(f"Devices available: {addresses}")
    return addresses


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(640, 480)

        self._client = None
        self._devices = []
        scan_button = QPushButton("Scan Devices")
        self.devices_combobox = QComboBox()
        connect_button = QPushButton("Connect")
        self.message_lineedit = QLineEdit()
        send_button = QPushButton("Send Message")
        self.log_edit = QPlainTextEdit()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        lay = QVBoxLayout(central_widget)
        lay.addWidget(scan_button)
        lay.addWidget(self.devices_combobox)
        lay.addWidget(connect_button)
        lay.addWidget(self.message_lineedit)
        lay.addWidget(send_button)
        lay.addWidget(self.log_edit)

        scan_button.clicked.connect(self.handle_scan)
        connect_button.clicked.connect(self.handle_connect)
        send_button.clicked.connect(self.handle_send)

    @property
    def devices(self):
        return self._devices

    @property
    def current_client(self):
        return self._client

    async def build_client(self, uuid, devname):
        if self._client is not None:
            await self._client.stop()
        self._client = QARIMUCLient(uuid, devname)
        self._client.new_data.connect(self.handle_new_data)
        await self._client.start_stream()
        self.log_edit.appendPlainText("connected")

    @qasync.asyncSlot()
    async def handle_connect(self):
        self.log_edit.appendPlainText("try connect")
        await self.build_client(self.devices_combobox.currentText(),
                                self.devices_combobox.currentData())

    @qasync.asyncSlot()
    async def handle_scan(self):
        self.log_edit.appendPlainText("Started scanner")
        self.devices.clear()
        devices = await find_devices(["imu_left", "imu_right"])
        self._devices = devices
        self.log_edit.appendPlainText(str(self.devices))
        self.devices_combobox.clear()
        for _d in self.devices:
            self.devices_combobox.addItem(_d, self.devices[_d])
        self.log_edit.appendPlainText("Finish scanner")

    def handle_new_data(self, msg):
        self.log_edit.appendPlainText(f"msg: {self._client.data['ax']}")
        
    @qasync.asyncSlot()
    async def handle_send(self):
        if self.current_client is None:
            return
        message = self.message_lineedit.text()
        if message:
            await self.current_client.write(message.encode())

def main():
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    w = MainWindow()
    w.show()
    with loop:
        loop.run_forever()


if __name__ == "__main__":
    # Logger
    logging.basicConfig(filename="log.log",
                        format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.INFO)
    main()