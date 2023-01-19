# Module implementing the JEDI serial communication protocol.
#
# Author: Sivakumar Balasubramanian
# Date: 12 July 2022
# Email: siva82kb@gmail.com


from re import S
import serial
import enum
import threading
import sys
import time
from serial.tools.list_ports import comports

class JediParsingStates(enum.Enum):
    LookingForHeader = 0
    FoundHeader1 = 1
    FoundHeader2 = 2
    ReadingPayload = 3
    CheckCheckSum = 4
    FoundFullPacket = 5


class JediComm(threading.Thread):
    
    def __init__(self, port, baudrate=115200, inform=None) -> None:
        super().__init__()
        self._port = port
        self._baudrate = baudrate
        self._ser = serial.Serial(port, baudrate)
        self._state = JediParsingStates.LookingForHeader
        self._inform = inform
        self._in_payload = []
        self._out_payload = []
        
        # Payload reading variables.
        self._N = 0
        self._cnt = 0
        self._chksum = 0
        
        # thread related variables.
        self._abort = False
        self._sleeping = False
        self.setDaemon(False)
    
    @property
    def sleeping(self):
        """ Returns if the thread is sleeping.
        """
        return self._sleeping

    def send_message(self, outbytes):
        _outpayload = [255, 255, len(outbytes)+1, *outbytes]
        _outpayload.append(sum(_outpayload) % 256)
        # Send payload.
        self._ser.write(bytearray(_outpayload))

    def run(self):
        """
        Thread operation.
        """
        self._state = JediParsingStates.LookingForHeader
        while True:
            # check if the currently paused
            if self._sleeping:
                # wait till the thread is un-paused.
                continue

            # abort?
            if self._abort is True:
                return

            self._read_handle_data()

    def sleep(self):
        """
        Puts the current thread in a paused state.
        """
        # with self.state:
        self._sleeping = True

    def wakeup(self):
        """
        Wake up a paused thread.
        """
        self._sleeping = False

    def abort(self):
        """
        Aborts the current thread.
        """
        self._abort = True
        self._ser.close()
        if self._sleeping:
            self.wakeup()

    def _read_handle_data(self):
        """
        Reads and handles the received data by calling the inform function.
        """
        # Read full packets.
        # if self._ser.inWaiting():
        #     sys.stdout.write("\nNew data: ")
        while self._ser.inWaiting():
            _byte = self._ser.read()
            # sys.stdout.write(f"{ord(_byte)} ")
            if self._state == JediParsingStates.LookingForHeader:
                if ord(_byte) == 0xff:
                    self._state = JediParsingStates.FoundHeader1
            elif self._state == JediParsingStates.FoundHeader1:
                if ord(_byte) == 0xff:
                    self._state = JediParsingStates.FoundHeader2
                else:
                    self._state = JediParsingStates.LookingForHeader
            elif self._state == JediParsingStates.FoundHeader2:
                self._N = ord(_byte)
                self._cnt = 0
                self._chksum = 255 + 255 + self._N
                self._in_payload = [ None ] * (self._N - 1)
                self._state = JediParsingStates.ReadingPayload
            elif self._state == JediParsingStates.ReadingPayload:
                self._in_payload[self._cnt] = ord(_byte)
                self._chksum += ord(_byte)
                self._cnt += 1
                if self._cnt == self._N - 1:
                    self._state = JediParsingStates.CheckCheckSum
            elif self._state == JediParsingStates.CheckCheckSum:
                if self._chksum % 256 == ord(_byte):
                    self._state = JediParsingStates.FoundFullPacket
                else:
                    self._state = JediParsingStates.LookingForHeader
            
            # Handle full packet.
            if self._state == JediParsingStates.FoundFullPacket:
                self._inform(self._in_payload)
                self._state = JediParsingStates.LookingForHeader



if __name__ == '__main__':
    def print_packet(packet):
        print("New packet: ", packet)
    
    jedireader = JediComm("COM16", 115200, print_packet)
    jedireader.start()
    time.sleep(10)
    jedireader.abort()