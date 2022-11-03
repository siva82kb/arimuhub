# Module implementing asynchronous communication with ARIMU using
# the JEDI protocol.
#
# Author: Sivakumar Balasubramanian
# Date: 20 July 2022
# Email: siva82kb@gmail.com


import serial
import enum
import sys
import time
import struct
from datetime import datetime as dt
import asyncio
from serial.tools.list_ports import comports

_DEBUG = False

# Jedi parsing states
class JediParsingStates(enum.Enum):
    LookingForHeader = 0
    FoundHeader1 = 1
    FoundHeader2 = 2
    ReadingPayload = 3
    CheckCheckSum = 4
    FoundFullPacket = 5

# ARIMU Errors
Error_Types1 = ["ImuIntFail",
                "SdNoCont",
                "RtcNoSet",
                "DatFlNoCrt",
                "DatFlNoRdl",
                "DatFlNoFnd"]

# ARIMU Commands
class ArimuCommands(object):
    STATUS = 0
    PING = 1
    LISTFILES = 2
    GETFILEDATA = 3
    DELETEFILE = 4
    GETMICROS = 5
    SETTIME = 6
    GETTIME = 7
    STARTSTREAM = 8
    STOPSTREAM = 9
    SETSUBJECT = 10
    GETSUBJECT = 11
    STARTEXPT = 12
    STOPEXPT = 13
    STARTDOCKSTNCOMM = 14
    STOPDOCKSTNCOMM = 15
    DOCKSTNPING = 16
    STARTNORMAL = 17
    STOPNORMAL = 18
    SETTONONE = 19
    CURRENTFILENAME = 128

# Other constants
class ArimuAdditionalFlags(object):
    NOFILE = 0
    FILESEARCHING = 1
    FILEHEADER = 2
    FILECONTENT = 3
    FILEDELETED = 4
    FILENOTDELETED = 5
    
    @staticmethod
    def flag_name(val):
        addl_flag_text = ["NOFILE",
                          "FILESEARCHING",
                          "FILEHEADER",
                          "FILECONTENT",
                          "FILEDELETED",
                          "FILENOTDELETED",]
        return addl_flag_text[val]

# ARIMU States.
class ArimuStates(object):
    NONE = 0
    BADERROR = 1
    NORMAL = 2
    EXPERIMENT = 3
    DOCKSTNCOMM = 4
    STREAMING = 5
    
    @staticmethod
    def state_name(val):
        state_text = ["NONE",
                      "BADERROR",
                      "NORMAL",
                      "EXPERIMENT",
                      "DOCKSTNCOMM",
                      "STREAMING",]
        return state_text[val] if val > 0 else ""


def get_number_bits(num):
    return  [int(x) for x in '{:08b}'.format(num)]


# Asynchronous ARIMU Class
class ArimuAsync(object):
    
    def __init__(self, comport, baudrate=115200):
        self.comport = comport
        self.baurdate = baudrate
        self.cmd_delay = 0.1
        self._client = serial.Serial(comport, baudrate)
        time.sleep(2)
        
    def close(self):
        self._client.close()

    async def status(self, timeout=0.5):
        """STATUS and await response."""
        # Write the PING message.
        self.send_jedi_message([ArimuCommands.STATUS])
        await asyncio.sleep(self.cmd_delay)
        _resp = await self.read_jedi_packet(ArimuCommands.STATUS,
                                            timeout)
        if _resp is None:
            return (None, None, None, None)
        else:
            return (_resp[0], _resp[1], _resp[2], _resp[3:])
    
    async def ping(self, timeout=0.5):
        """PING and await response."""
        # Write the PING message.
        self.send_jedi_message([ArimuCommands.PING])
        await asyncio.sleep(self.cmd_delay)
        _resp = await self.read_jedi_packet(ArimuCommands.PING,
                                            timeout)
        if _resp is None:
            return (None, None, None, None)
        else:
            return (_resp[0], _resp[1], _resp[2], _resp[3:])

    async def dockstnping(self, timeout=0.5):
        """DOCKSTNPING."""
        # Write the PING message.
        self.send_jedi_message([ArimuCommands.DOCKSTNPING])
        await asyncio.sleep(self.cmd_delay)
        return (None, None, None, None)
    
    async def startdockstncomm(self, timeout=0.5):
        """STARTDOCKSTNCOMM and await response."""
        # Write the PING message.
        self.send_jedi_message([ArimuCommands.STARTDOCKSTNCOMM])
        await asyncio.sleep(self.cmd_delay)
        _resp = await self.read_jedi_packet(ArimuCommands.STARTDOCKSTNCOMM,
                                            timeout)
        if _resp is None:
            return (None, None, None, None)
        else:
            return (_resp[0], _resp[1], _resp[2], _resp[3:])
    
    async def stopdockstncomm(self, timeout=0.5):
        """STOPDOCKSTNCOMM and await response."""
        # Write the PING message.
        self.send_jedi_message([ArimuCommands.STOPDOCKSTNCOMM])
        await asyncio.sleep(self.cmd_delay)
        _resp = await self.read_jedi_packet(ArimuCommands.STOPDOCKSTNCOMM,
                                            timeout)
        if _resp is None:
            return (None, None, None, None)
        else:
            return (_resp[0], _resp[1], _resp[2], _resp[3:])
    
    async def startnormal(self, timeout=0.5):
        """STARTNORMAL and await response."""
        # Write the PING message.
        self.send_jedi_message([ArimuCommands.STARTNORMAL])
        await asyncio.sleep(self.cmd_delay)
        _resp = await self.read_jedi_packet(ArimuCommands.STARTNORMAL,
                                            timeout)
        if _resp is None:
            return (None, None, None, None)
        else:
            return (_resp[0], _resp[1], _resp[2], _resp[3:])
    
    async def stopnormal(self, timeout=0.5):
        """STOPNORMAL and await response."""
        # Write the PING message.
        self.send_jedi_message([ArimuCommands.STOPNORMAL])
        await asyncio.sleep(self.cmd_delay)
        _resp = await self.read_jedi_packet(ArimuCommands.STOPNORMAL,
                                            timeout)
        if _resp is None:
            return (None, None, None, None)
        else:
            return (_resp[0], _resp[1], _resp[2], _resp[3:])
    
    async def startexpt(self, timeout=0.5):
        """STARTEXPT and await response."""
        # Write the PING message.
        self.send_jedi_message([ArimuCommands.STARTEXPT])
        await asyncio.sleep(self.cmd_delay)
        _resp = await self.read_jedi_packet(ArimuCommands.STARTEXPT,
                                            timeout)
        if _resp is None:
            return (None, None, None, None)
        else:
            return (_resp[0], _resp[1], _resp[2], _resp[3:])
    
    async def stopexpt(self, timeout=0.5):
        """STOPEXPT and await response."""
        # Write the PING message.
        self.send_jedi_message([ArimuCommands.STOPEXPT])
        await asyncio.sleep(self.cmd_delay)
        _resp = await self.read_jedi_packet(ArimuCommands.STOPEXPT,
                                            timeout)
        if _resp is None:
            return (None, None, None, None)
        else:
            return (_resp[0], _resp[1], _resp[2], _resp[3:])
    
    async def startstream(self, timeout=0.5):
        """STARTSTREAM and await response."""
        # Write the PING message.
        self.send_jedi_message([ArimuCommands.STARTSTREAM])
        await asyncio.sleep(self.cmd_delay)
        _resp = await self.read_jedi_packet(ArimuCommands.STARTSTREAM,
                                            timeout)
        if _resp is None:
            return (None, None, None, None)
        else:
            return (_resp[0], _resp[1], _resp[2], _resp[3:])
    
    async def stopstream(self, timeout=0.5):
        """STOPSTREAM and await response."""
        # Write the PING message.
        self.send_jedi_message([ArimuCommands.STOPSTREAM])
        await asyncio.sleep(self.cmd_delay)
        _resp = await self.read_jedi_packet(ArimuCommands.STOPSTREAM,
                                            timeout)
        if _resp is None:
            return (None, None, None, None)
        else:
            return (_resp[0], _resp[1], _resp[2], _resp[3:])
    
    async def settonone(self, timeout=0.5):
        """SETTONONE and await response."""
        # Write the SETTONONE message.
        self.send_jedi_message([ArimuCommands.SETTONONE])
        await asyncio.sleep(self.cmd_delay)
        _resp = await self.read_jedi_packet(ArimuCommands.SETTONONE,
                                            timeout)
        if _resp is None:
            return (None, None, None, None)
        else:
            return (_resp[0], _resp[1], _resp[2], _resp[3:])

    async def setsubject(self, subjname, timeout=0.5):
        """SETSUBJECT and await respose."""
        self.send_jedi_message(bytearray([ArimuCommands.SETSUBJECT])
                               + bytearray(subjname, "ascii")
                               + bytearray([0]))
        await asyncio.sleep(self.cmd_delay)
        _resp = await self.read_jedi_packet(ArimuCommands.SETSUBJECT,
                                            timeout)
        if _resp is None:
            return (None, None, None, None)
        else:
            return (_resp[0], _resp[1], _resp[2], _resp[3:])
    
    async def getsubject(self, timeout=0.5):
        """GETSUBJECT and await respose."""
        self.send_jedi_message([ArimuCommands.GETSUBJECT])
        await asyncio.sleep(self.cmd_delay)
        _resp = await self.read_jedi_packet(ArimuCommands.GETSUBJECT,
                                            timeout)
        if _resp is None:
            return (None, None, None, None)
        else:
            return (_resp[0], _resp[1], _resp[2], _resp[3:])
    
    async def settime(self, timeout=0.5):
        """SETTIME using the current time and await response."""
        return await self.settime(dt.now(), timeout)
    
    async def settime(self, dtvalue, timeout=0.5):
        """SETTIME using the given timee 'dtvalue' and await response."""
        _dtvals = (struct.pack("<L", dtvalue.year % 100)
                   + struct.pack("<L", dtvalue.month)
                   + struct.pack("<L", dtvalue.day)
                   + struct.pack("<L", dtvalue.hour)
                   + struct.pack("<L", dtvalue.minute)
                   + struct.pack("<L", dtvalue.second)
                   + struct.pack("<L", dtvalue.microsecond // 10000))
        self.send_jedi_message(bytearray([ArimuCommands.SETTIME]) + _dtvals)
        await asyncio.sleep(self.cmd_delay)
        _resp = await self.read_jedi_packet(ArimuCommands.SETTIME,
                                            timeout)
        # Decode into current time and micros.
        if _resp is None:
            return (None, None, None, None)
        else:
            return (_resp[0], _resp[1], _resp[2],
                    self._decode_setgettime_resp(_resp[3:]))
        
    async def gettime(self, timeout=0.5):
        """GETTIME and await response."""
        self.send_jedi_message([ArimuCommands.GETTIME])
        await asyncio.sleep(self.cmd_delay)
        _resp = await self.read_jedi_packet(ArimuCommands.GETTIME,
                                            timeout=1.0)
        if _resp is None:
            return (None, None, None, None)
        else:
            return (_resp[0], _resp[1], _resp[2],
                    self._decode_setgettime_resp(_resp[3:]))
    
    async def listfiles(self, timeout=0.5):
        """LISTFILE and await response."""
        self.send_jedi_message([ArimuCommands.LISTFILES])
        await asyncio.sleep(self.cmd_delay)
        while True:
            _resp = await self.read_jedi_packet(ArimuCommands.LISTFILES,
                                                timeout=timeout)
            await asyncio.sleep(0.05)
            # Failed to read the response.
            if _resp is None:
                yield (None, None, None, None)
                break
            # Valid response.
            _str = bytearray(_resp[3:]).decode()
            if len(_str) == 0:
                yield (None, None, None, None)
                break
            if _str[0] == '[':
                # Create a new list.
                yield (_resp[0], _resp[1], _resp[2], _str[1:-1].split(","))
            else:
                yield (_resp[0], _resp[1], _resp[2], _str[0:-1].split(","))
            # Check if end of list is reached.
            if _str[-1] == ']':
                break
    
    async def getfiledata(self, fname, timeout=1.0):
        """GETFILEDATA and await response."""
        self.send_jedi_message(bytearray([ArimuCommands.GETFILEDATA])
                               + bytearray(fname, "ascii")
                               + bytearray([0]))
        await asyncio.sleep(self.cmd_delay)
        # Read file data and yield.
        while True:
            _resp = await self.read_jedi_packet(ArimuCommands.GETFILEDATA,
                                                timeout=5.0)
            if _resp is None:
                yield (None, None, None, None)
                break
            else:
                if _resp[3] == ArimuAdditionalFlags.NOFILE:
                    yield (_resp[0], _resp[1], _resp[2],
                           (_resp[3],))
                elif _resp[3] == ArimuAdditionalFlags.FILEHEADER:
                    yield (_resp[0], _resp[1], _resp[2],
                           (_resp[3],
                            struct.unpack('<L', bytearray(_resp[4:8]))[0]))
                elif _resp[3] == ArimuAdditionalFlags.FILECONTENT:
                    if _resp[4] == 255:
                        yield (_resp[0], _resp[1], _resp[2],
                               (_resp[3], _resp[4], bytearray(_resp[5:])))
                        break
                    else:
                        yield (_resp[0], _resp[1], _resp[2],
                               (_resp[3], _resp[4], bytearray(_resp[5:])))
    
    async def deletefile(self, fname):
        """DELETEFILE and await response."""
        self.send_jedi_message(bytearray([ArimuCommands.DELETEFILE])
                               + bytearray(fname, "ascii")
                               + bytearray([0]))
        await asyncio.sleep(self.cmd_delay)
        _resp = await self.read_jedi_packet(ArimuCommands.DELETEFILE,
                                            timeout=0.5)
        if _resp is None:
            return (None, None, None, None)
        else:
            return (_resp[0], _resp[1], _resp[2], _resp[3])
        
    def _decode_setgettime_resp(self, payload):
        """Decodes the payload received from SETTIME and GETTIME to current
        time and micros."""
        # Current time data.
        _pldbytes = [bytearray(payload[i:i+4]) for i in range(0, 28, 4)]
        _temp = [struct.unpack('<L', _pldbytes[i])[-1]
                 for i in range(7)]
        _ts = (f'{_temp[0]:02d}-{_temp[1]:02d}-{_temp[2]:02d}'
               + f'T{_temp[3]}:{_temp[4]}:{_temp[5]}.{_temp[6]}')
        _currt = dt.strptime(_ts, '%y-%m-%dT%H:%M:%S.%f')
        # Micros data.
        _microst = struct.unpack('<L', bytearray(payload[28:32]))[-1]
        return (_currt, _microst)

    def send_jedi_message(self, payload):
        """Send JEDI payload out."""
        _outpayload = [255, 255, len(payload)+1, *payload]
        _outpayload.append(sum(_outpayload) % 256)
        if _DEBUG:
            sys.stdout.write("\n Out Data: ")
            for _el in _outpayload:
                sys.stdout.write(f"{_el} ")
        self._client.write(bytearray(_outpayload))

    async def read_jedi_packet(self, cmd, timeout):
        """Read a fill JEDI packet with the command 'cmd' within
        'timeout' seconds."""
        _strt = time.time()
        _state = JediParsingStates.LookingForHeader
        if _DEBUG:
            sys.stdout.write("\n In Data: ")
        while time.time() - _strt <= timeout:
            # Read response.
            if not self._client.inWaiting():
                continue
            # Bytes available
            _byte = self._client.read()
            if _DEBUG:
                try:
                    sys.stdout.write(f"{bytearray([_byte]).decode()}")
                except:
                    sys.stdout.write(f"{ord(_byte)} ")
                sys.stdout.flush()
            if _state == JediParsingStates.LookingForHeader:
                if ord(_byte) == 0xff:
                    _state = JediParsingStates.FoundHeader1
            elif _state == JediParsingStates.FoundHeader1:
                if ord(_byte) == 0xff:
                    _state = JediParsingStates.FoundHeader2
                else:
                    _state = JediParsingStates.LookingForHeader
            elif _state == JediParsingStates.FoundHeader2:
                _N = ord(_byte)
                if _N > 0:
                    _cnt = 0
                    _chksum = 255 + 255 + _N
                    # sys.stdout.write(f"\n    {_N} - ")
                    _in_payload = [ None ] * (_N - 1)
                    _state = JediParsingStates.ReadingPayload
                else:
                    # Cannot be a valid packet.
                    _state = JediParsingStates.LookingForHeader
            elif _state == JediParsingStates.ReadingPayload:
                # sys.stdout.write(f" {_cnt}, {len(_in_payload)} | ")
                _in_payload[_cnt] = ord(_byte)
                _chksum += ord(_byte)
                _cnt += 1
                if _cnt == _N - 1:
                    _state = JediParsingStates.CheckCheckSum
            elif _state == JediParsingStates.CheckCheckSum:
                if _chksum % 256 == ord(_byte):
                    _state = JediParsingStates.FoundFullPacket
                    # Make sure the packet has the command we are looking for.
                    if _in_payload[0] == cmd:
                        # sys.stdout.write("\n")
                        return _in_payload
                _state = JediParsingStates.LookingForHeader
        # print(time.time() - _strt)
        # sys.stdout.write("\n")
        return None


async def test():
    arimu = ArimuAsync("COM16", 115200)
    await asyncio.sleep(2)
    print(await arimu.ping())
    print(await arimu.status())

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    tasks = [
        loop.create_task(test()),
    ]
    loop.run_until_complete(asyncio.wait(tasks))
    loop.close()