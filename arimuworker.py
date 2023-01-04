"""ARIMU Data Reader worker module.

Author: Sivakumar Balasubramanian
Date: 02 October 2022
Email: siva82kb@gmail.com
"""

from concurrent.futures import thread
import struct
import sys
from datetime import datetime as dt
from datetime import timedelta as tdel
import threading
import enum
from serial.tools.list_ports import comports
import itertools
import os
import json
import time
import glob
from asyncarimu import (ArimuAdditionalFlags,
                        ArimuCommands,
                        ArimuAsync,
                        ArimuStates,
                        Error_Types1,
                        get_number_bits)
from PyQt5 import (
    QtWidgets,)
from qtjedi import JediComm
from PyQt5.QtCore import pyqtSignal, QObject
from misc import (ProgressBar,)
import traceback
import attrdict


DTSTRFMT = "%y/%m/%d %H:%M:%S.%f"
LOGDTFMT = "%m/%d %H:%M:%S"


class DockStnStates(enum.Enum):
    WAIT_WRKPASS = 0
    WAIT_CONNECT = 1
    WORK_FILELST = 2
    WORK_FILEDAT = 3
    WORK_FILEDEL = 4
    WORK_RELAXNG = 5
    
    def __str__(self):
        return self.name


class DockStnReports(enum.Enum):
    NEW = 0
    APPEND = 1
    OVERWRITE = 2
    
    def __str__(self):
        return self.name


# Class to doing the different tests.
class ArimuDocWorker(QObject):
    # Number of log messages to remember.
    LOG_MSG_MAX_N = 100
    # Sleep periods.
    WORKPASS_WAIT_PERIOD = 5.0
    CONNECT_WAIT_PERIOD = 5.0
    STATE_CHANGE_WAIT_PERIOD = 1.0
    BREAK_PERIOD = 0.5
    DOCKSTN_PING_PERIOD = 1.0
    # Command retry count.
    MAX_CMD_RETRY_COUNT = 5
    # ARIMU communidation delays.
    ARIMU_FILELIST_TIMEOUT = 5.0
    # Maximum exception per state before a full reset.
    ARIMU_MAX_EXCEPT_COUNT = 5

    # Different signals used to communicate with external PyQT programs.
    connect_response = pyqtSignal(str)
    delayed_respose = pyqtSignal(ArimuCommands)
    file_list = pyqtSignal(list)
    file_data = pyqtSignal(list)


    def __init__(self, comport, subject, outdir, donotdelete=False):
        super(ArimuDocWorker, self).__init__()
        self.comport: str = comport
        self._comfound: bool = False
        self.subjname: str = subject
        self.outdir: str = outdir
        self.devname: str = ""
        self.donotdelete: bool  = donotdelete
        # 
        # ARIMU related variables
        self._arimustate = None
        self._arimuerr = None
        #
        # A flag for when a section of the code is waiting for response from
        # the ARIMU device.
        self.resp = attrdict.AttrDict({"msgtype": None,
                                       "callback": None,
                                       "timer": None})
        self._dockstn_start_function = None
        #
        # File list and file data variables.
        self._filelist = []
        self._filedata = None
        #
        # Terminator flag. This flag set to True will end the statemahcine.
        self.terminate = False
        #
        # Program state
        self._state = DockStnStates.WAIT_WRKPASS
        # self._resptimer = None
        # self._state_handlers = self.setup_state_handlers()
        #
        # Timer parameters.
        # self.stoptimer = False
        # self.pausetimer = False
        #
        # ARIMU device variables.
        # self.init_arimu_dev_variables()

    @property
    def state(self):
        """State property"""
        return self._state

    @property
    def comfound(self):
        """COM port found property"""
        return self._comfound

    def connect(self):
        """Try to connect the given COM port and return true if the device
        is an ARIMU."""
        self._client = JediComm(self.comport, 115200)
        self._client.newdata_signal.connect(self._handle_new_arimu_packets)
        self._client.start()
        time.sleep(0.5)
        # Get the status of the device.
        self.setup_response(ArimuCommands.PING,
                            self._update_connect_status)
        self._client.send_message([ArimuCommands.PING])
        self.resp.timer.start()

    def get_filelist(self):
        """Gets the list of file names from the ARIMU device, and informs
        about the final list."""
        # Check if the device is in the dockstation mode.
        if self._arimustate != ArimuStates.DOCKSTNCOMM:
            # First set the device in the docking station mode.
            # Set the device in the docking station mode.
            print("--")
            self.setup_response(ArimuCommands.STARTDOCKSTNCOMM,
                                self._update_docstnstart)
            self._dockstn_start_function = self.get_filelist
            self._client.send_message([ArimuCommands.STARTDOCKSTNCOMM])
            self.resp.timer.start()
            return

        # Now get the list of files.
        self.setup_response(ArimuCommands.LISTFILES,
                            self._update_filelist)
        self._client.send_message([ArimuCommands.LISTFILES])
        self.resp.timer.start()

    def get_file_data(self, filename):
        """Gets the data from the ARIMU device for the given file name, and
        informs when data is available."""
        # Check if the device is in the dockstation mode.
        if self._arimustate != ArimuStates.DOCKSTNCOMM:
            # First set the device in the docking station mode.
            # Set the device in the docking station mode.
            self.setup_response(ArimuCommands.STARTDOCKSTNCOMM,
                                self._update_docstnstart)
            self._dockstn_start_function = self.get_file_data
            self._client.send_message([ArimuCommands.STARTDOCKSTNCOMM])
            self.resp.timer.start()
            return

        # Noe get thr file data.
        self.setup_response(ArimuCommands.GETFILEDATA,
                            self._update_filedata)
        self._client.send_message(bytearray([ArimuCommands.GETFILEDATA])
                                  + bytearray(filename, "ascii")
                                  + bytearray([0]))
        self.resp.timer.start()

    def _delayed_response_handler(self):
        """Callback to handle when there is a delayed response from ARIMU
        for a sent command."""
        # Check if the response was obtained.
        # print("response not found")
        print(self.resp.msgtype)
        if self.resp.msgtype != None:
            # No response receied for some time. Cancel response, and inform
            # about the lack of response.
            self.delayed_respose.emit(self.resp.msgtype)
            self.clear_response()
    
    def _handle_new_arimu_packets(self, payload):
        """Call back for when new packets are received from the ARIMU device.
        """
        # Handle packet.
        _cmd, _state, _err, *_pl = payload
        self._arimustate = _state
        self._arimuerr = _err
        
        # Check if expect message was received.
        if self.resp.msgtype == _cmd:
            # First stop the response timer.
            self.resp.timer.cancel()
            self.resp.callback(_pl)
        
    def setup_response(self, cmd, cbfunc):
        """Function to set up the resp attrdict for receiving and handling a
        response from ARIMU."""
        self.resp.msgtype = cmd
        self.resp.callback = cbfunc
        self.resp.timer = threading.Timer(2.0, self._delayed_response_handler)
    
    def clear_response(self):
        """Clears resp to indicate that we are not expecting any new responses
        from ARIMU."""
        # print("lala")
        self.resp.timer.cancel()
        self.resp.msgtype = None
        self.resp.callback = None
        self.resp.timer = None
        
    def _update_connect_status(self, pl):
        """Updates the connection status of the device. It will be connected
        only of the other device is an ARIMU."""
        # Check if the name of the device is correct.
        if "ARIMU" in bytearray(pl).decode():
            self.devname = bytearray(pl).decode()
        else:
            self.devname = ""
        # Emit connected signal
        self.connect_response.emit(self.devname)
    
    def _update_filelist(self, pl):
        """Update the list of files on the device.
        """
        _str = bytearray(pl[:]).decode()
        if len(_str) == 0:
            self.file_list.emit([])
        if _str[0] != '[':
            # Create a new list.
            _temp = _str[0:-1].split(",")
        else:
            _temp = _str[1:-1].split(",")
        self.file_list.emit([_fl for _fl in _temp if len(_fl) > 0])
        
        # Check if end of list is reached.
        if _str[-1] == ']':
            # Clear file list and include only non-zero length file names.
            self.file_list.emit([])
            
    def _update_filedata(self, pl):
        """Update the file data on the device.
        """
        if pl[0] == ArimuAdditionalFlags.NOFILE:
            self.file_data.emit([ArimuAdditionalFlags.NOFILE,])
        elif pl[0] == ArimuAdditionalFlags.FILEHEADER:
            # Unpack and emit file details.
            _totsz = struct.unpack('<L', bytearray(pl[1:5]))[0]
            self.file_data.emit([ArimuAdditionalFlags.FILEHEADER, _totsz])
        # elif pl[0] == ArimuAdditionalFlags.FILECONTENT:
        #     # Write to file.
        #     self._currfiledetails.currsz += len(pl[2:])
        #     # Update progress bar
        #     _pbstr, _prcnt = self._currfiledetails.prgbar.update(pl[1])
        #     self._currfiledetails.handle.write(bytearray(pl[2:]))
        #     # Display string
        #     _str = [f"|{_pbstr}|",
        #             f"[{_prcnt:6.2f}%]",
        #             f"[{self._currfiledetails.currsz/1024:8.2f}kB /",
        #             f"{self._currfiledetails.totalsz/1024:8.2f}kB]",]
        #     self.lbl_status.setText(f"{' '.join(_str)}")
        #     # Check if the file has been obtained.
        #     if _prcnt >= 100:
        #         self._statusdisp = False
        #         self._currfiledetails.handle
        #         self.display_response(f"File data reading done! File {self._currfiledetails.name} saved!")
    
    def _update_docstnstart(self, pl):
        """Function to handle when the DOCKSTATION mode is started.
        """
        # Check if there is a function waiting for ARIMU to be set in the
        # Dockstation mode.
        if self._dockstn_start_function is not None:
            self._dockstn_start_function()
    
    def get_dev_err_str(self):
        return ArimuDocWorker.get_err_str(self.arimu_err)
    
    def get_log_msgs(self, lastn=10):
        return self._log_msgs[-lastn:]
        
    def get_gui_log_msgs(self, lastn=10):
        return self._gui_log_msgs[-lastn:]
    
    def get_short_log_msgs(self, lastn=10):
        return self._short_msgs[-lastn:]
    
    def setup_state_handlers(self):
        """Returns the dictionary of state and state handler class function
        for running the state machine."""
        return {
            DockStnStates.WAIT_WRKPASS: self.handle_wait_for_workpass,
            DockStnStates.WAIT_CONNECT: self.handle_wait_for_connect,
            DockStnStates.WORK_FILELST: self.handle_working_filelist,
            DockStnStates.WORK_FILEDAT: self.handle_working_filedata,
            DockStnStates.WORK_FILEDEL: self.handle_working_filedelete,
            DockStnStates.WORK_RELAXNG: self.handle_worker_idle,
        }
    
    # async def take_a_break(self):
    #     """Function called to stop the execution of the state machine to let
    #     other coroutines to run."""
    #     await asyncio.sleep(ArimuDocWorker.BREAK_PERIOD)
    
    def init_arimu_dev_variables(self):
        """Function to initialize all variables for communcating with ARIMU."""
        # Return work pass. In case this is called when there was an error
        # during the operation of the state machine.
        ArimuDocWorker.return_work_pass(self.comport)
        #
        # Device stuff
        try:
            self.arimu.close()
        except Exception as e:
            pass
        self.arimu = None
        self.arimu_state = -1
        self.arimu_err = 0
        self.devname = ""
        #
        # How long was the device connected?
        self.connected_time = -1
        #
        # Saving messages during the operation of the device.
        self._msgs = []
        self._short_msgs = []
        self._gui_log_msgs = []
        #
        # Progarm parameters
        self.params_file:str = None
        self.params:dict = None
        self.exception_count:int = 0
        self.currfiles:dict = None 
        self.sess_time:dt = None
        self.sess_time_str:str = None
        self.sess_data_dir:str = None
    
    def report(self, msg, rtype:DockStnReports = DockStnReports.NEW):
        """Function to print messages to the stdout."""
        _str = '  '.join((
            dt.now().strftime(LOGDTFMT),
            f"{self.comport:<15}",
            f"{self.state}",
            f"{ArimuStates.state_name(self.arimu_state):<12}",
            "|"
        ))
        if rtype == DockStnReports.NEW:
            sys.stdout.write("\n" + _str + " ")
            self._msgs.append(_str)
        elif rtype == DockStnReports.OVERWRITE:
            sys.stdout.write("\r" + _str + " ")
            self._msgs[-1] = _str
        sys.stdout.write(msg)
        self._msgs[-1] = self._msgs[-1] + msg
        sys.stdout.flush()
        #
        # Ensure length is maintained.
        if len(self._msgs) > ArimuDocWorker.LOG_MSG_MAX_N:
            self._msgs.pop(0)
    
    def log_short_message(self, msg, rtype:DockStnReports = DockStnReports.NEW):
        """Saves messages for other programs to use."""
        if rtype == DockStnReports.NEW:
            self._short_msgs.append(msg)
        elif rtype == DockStnReports.OVERWRITE:
            self._short_msgs[-1] = msg
        else:
            self._short_msgs[-1] = self._short_msgs[-1] + msg
        #
        # Ensure length is maintained.
        if len(self._short_msgs) > ArimuDocWorker.LOG_MSG_MAX_N:
            self._short_msgs.pop(0)
    
#     def start(self):
#         """Executes the docking station state machine."""
#         while not self.terminate:
#             try:
#                 await self._state_handlers[self.state]()
#             except Exception as e:
#                 self.report(
#                     "Exception found! Error in the state machine. "
#                     + "Details are given below."
#                 )
#                 print("\n")
#                 print(e)
#                 traceback.print_exc()
#                 self.log_short_message("Error with serial connection.")
#                 break    
#             await self.take_a_break()
#         self.stoptimer = True
    
#     async def timer(self):
#         """Timer function that send DOCKSTNPIN messages."""
#         _on, _off = "|O|", "| |"
#         _prev = _on
#         while self.stoptimer is False:
#             await asyncio.sleep(ArimuDocWorker.DOCKSTN_PING_PERIOD)
#             if self.connected_time >= 0:
#                 self.connected_time += ArimuDocWorker.DOCKSTN_PING_PERIOD
#             # DOCKSTNPING to keep the connection alive.
#             if (self.pausetimer is False
#                 and self.arimu_state == ArimuStates.DOCKSTNCOMM):
#                 try:
#                     # Check state.
#                     if self.state == DockStnStates.WORK_RELAXNG:
#                         await self._timer_work_relaxng()
#                     else:
#                         _ = await self.arimu.dockstnping()
#                         self.report(">", rtype=DockStnReports.APPEND)
#                 except Exception as e:
#                     self.report(
#                         "Error during dockstation pinging. Reconneting."
#                     )
#                     print("\n")
#                     print(e)
#                     traceback.print_exc()
#                     self.log_short_message("Error during dockstation pinging.")
#                     # await self._restart_connection()
#                     self._change_state_to(DockStnStates.WAIT_FOR_CONNECT)
#                     break

#     async def _timer_work_relaxng(self):
#         """Function to do things in the timer function when the program
#         is in WORK_RELAXNG mode."""
#         _currt = dt.now()
#         if await self._set_device_time(_currt):
#             self.report(
#                 f"Setting time to {_currt.strftime(DTSTRFMT)}",
#                 rtype=DockStnReports.OVERWRITE
#             )
#             self.log_short_message(
#                 f"Setting time to {_currt.strftime(DTSTRFMT)}",
#                 rtype=DockStnReports.OVERWRITE
#             )
#             return
        
#     async def _restart_connection(self):
#         self.report("Restarting connection.")
#         self.log_short_message("Restarting connection.")
#         try:
#             self.arimu.close()
#         except:
#             pass
#         ArimuDocWorker.return_work_pass(self.comport)
#         self.init_arimu_dev_variables()
#         await self._change_state_to(DockStnStates.WAIT_WRKPASS)
#         await self.take_a_break()

#     async def _change_state_to(self, newstate):
#         """Function to change state with the appropraite book keeping."""
#         if newstate == self._state:
#             return
#         # Reset exception count.
#         self.exception_count = 0
#         if newstate == DockStnStates.WAIT_WRKPASS:
#             # Stateing out. All variable must eb reset to the inital state.
#             self.init_arimu_dev_variables()
#         elif newstate == DockStnStates.WAIT_CONNECT:
#             # Got work pass.
#             pass
#         elif newstate == DockStnStates.WORK_FILELST:
#             pass
#         elif newstate == DockStnStates.WORK_FILEDAT:
#             pass
#         elif newstate == DockStnStates.WORK_RELAXNG:
#             # Set to DOCKSTNCOMM mode.
#             _, _st, _er, _pl = await self.arimu.startdockstncomm()
#             self._update_dev_state_error(_st, _er)
#             pass
        
#         # Change state
#         self._state = newstate
#         self.report(
#             f"Changed state to {self._state}"
#         )
#         self.log_short_message(
#             f"Changed state to {self._state}"
#         )
#         await asyncio.sleep(ArimuDocWorker.STATE_CHANGE_WAIT_PERIOD)
    
#     def _get_params_data(self, currdt):
#         """Reads/Creates the dictionary with program parameter details."""
#         try:
#             with open(self.params_file, 'r') as fh:
#                 _params = json.load(fh)
#         except (FileNotFoundError, json.decoder.JSONDecodeError):
#             _params = {'subjname': self.subjname,
#                        'devname': self.devname,
#                        'setgettime': {},
#                        'files': {},
#                        'deleted': []
#                        }
#             self.report("Created params file.")
#         # Get time and store it.
#         _params["setgettime"][currdt] = {
#             "get": None,
#             "set": None,
#         }
#         return _params
    
#     def _init_post_connect_stuff(self):
#         """Function to initialize variable post-connected to ARIMU."""
#         self.sess_time = dt.now()
#         self.sess_time_str = self.sess_time.strftime(DTSTRFMT)
#         self.connected_time = 0
#         self.sess_data_dir = os.sep.join((
#             self.outdir,
#             self.subjname,
#             self.devname,
#         ))
#         # Create the directory if it does not exist.
#         if not os.path.exists(self.sess_data_dir):
#             os.makedirs(self.sess_data_dir)
#         self.params_file = os.sep.join((
#             self.sess_data_dir,
#             f"prgparams_{self.devname.split('_')[-1]}.json"
#         ))
#         # Read parameter file and initialize segments.
#         self.params = self._get_params_data(self.sess_time_str)
    
#     async def handle_wait_for_workpass(self):
#         """Handles WAIT_FOR_WORKPASS state."""
#         #
#         # Wait for the serial port just to inform about the status of the port.
#         self.report(f"Waiting for port {self.comport}")
#         self.log_short_message(f"Waiting for port {self.comport}")
#         _waiting = True
#         while _waiting:
#             _cports = [p.name for p in comports()]
#             _waiting = self.comport not in _cports
#             await asyncio.sleep(ArimuDocWorker.CONNECT_WAIT_PERIOD)
#         self._comfound = True
#         self.report(f"Found port {self.comport}")
#         self.log_short_message(f"Found port {self.comport}")
#         #
#         # First get the work pass.
#         self.report("Waiting for work pass.")
#         self.log_short_message(f"Waiting for work pass {dt.now().strftime('%d/%m %H:%M:%S')}.")
#         while not ArimuDocWorker.get_work_pass(self.comport):
#             self.log_short_message(f"Waiting for work pass {dt.now().strftime('%d/%m %H:%M:%S')}.",
#                                    rtype=DockStnReports.OVERWRITE)
#             await asyncio.sleep(ArimuDocWorker.WORKPASS_WAIT_PERIOD)
#         _msg = f"Got work pass (worker id: {ArimuDocWorker.worker_id_holding_pass()})."
#         self.report(_msg)
#         self.log_short_message(_msg)
#         await self._change_state_to(DockStnStates.WAIT_CONNECT)
    
#     async def handle_wait_for_connect(self):
#         """Handles the WAIT_FOR_CONNECT state."""
#         # Waiting for PORT and connect.
#         if not await self._wait_and_connect():
#             # Some error connecting. Go back and try again.
#             self._change_state_to(DockStnStates.WAIT_WRKPASS)
#             return

#         # Get the name of the device.
#         if not await self._get_device_name():
#             # Device name could not be obtained.
#             self._change_state_to(DockStnStates.WAIT_WRKPASS)
#             return
            
#         # Initialize stuff post-connected.
#         self._init_post_connect_stuff()
        
#         # Get the current time.
#         if not await self._get_device_time():
#             # Device time could not be obtained.
#             self._change_state_to(DockStnStates.WAIT_WRKPASS)
#             return
        
#         # Set device to DOCKSTNCOMM mode.
#         if not await self._set_device_to_dockstncomm_state():
#             # Device could not be set to DOCKSTNCOMM mode.
#             self._change_state_to(DockStnStates.WAIT_WRKPASS)
#             return
        
#         # Set device time.
#         _currt = dt.now()
#         if not await self._set_device_time(_currt):
#             # Unable to set to NONE state.
#             self._change_state_to(DockStnStates.WAIT_WRKPASS)
#             return

#         # Set device to NONE mode.
#         if not await self._set_device_to_none_state():
#             # Device could not be set to NONE mode.
#             self._change_state_to(DockStnStates.WAIT_WRKPASS)
#             return
        
#         await self._change_state_to(DockStnStates.WORK_FILELST)
        
#     async def handle_working_filelist(self):
#         """Handles the WORKING_FILELIST state."""
#         # Set device to DOCKSTNCOMM mode.
#         if not await self._set_device_to_dockstncomm_state():
#             # Device could not be set to DOCKSTNCOMM mode.
#             self._change_state_to(DockStnStates.WAIT_WRKPASS)
#             return
#         await self.take_a_break()
        
#         # Get the list of all files.
#         _alldevfiles = [_fl for _fl in await self._get_device_filelist()
#                         if self.subjname in _fl]

#         # Find the list of new files to be read from the device.
#         _fgot, _fnogot = self._get_prev_files_list()
#         print(_fgot, _fnogot)
        
#         # Details about the files read now.
#         self.currfiles = {"got": [], "nogot": [], "toget": []}
#         self.currfiles["toget"] = [_fl for _fl in _alldevfiles
#                                    if _fl not in (_fgot + _fnogot)]
#         self.params["files"][self.sess_time_str] = self.currfiles
#         self.report(
#             f"Total of "
#             + f"{len(self.currfiles['toget'])}"
#             + " to get."
#         )
#         await self._change_state_to(DockStnStates.WORK_FILEDAT)
    
#     async def handle_working_filedata(self):
#         """Handles the WORKING_FILEDAT state."""
#         await self.take_a_break()
        
#         _alldur = 0
#         _n, _N = 0, len(self.currfiles["toget"])
#         while len(self.currfiles["toget"]) > 0:
#             # Get the next file to get.
#             _fname = self.currfiles["toget"][0]
#             _fdetails = self._init_file_to_get_details(_n, _N, _fname)
            
#             # Set device to DOCKSTNCOMM mode.
#             if not await self._set_device_to_dockstncomm_state():
#                 # Could not get the decice in DOCKSTNCOMM mode.
#                 self.report("Could not set DOCKSTNCOMM mode.")
#                 self.log_short_message("Could not set DOCKSTNCOMM mode.")
#                 # Increment exception count.
#                 self.exception_count += 1
#                 if self.exception_count >= ArimuDocWorker.ARIMU_MAX_EXCEPT_COUNT:
#                     await self._restart_connection()
#                     return
#                 continue
            
#             # Read and save file data
#             _tdur = await self._get_write_filedata(_fdetails)
            
#             # Check if the file was read and saved.
#             if _tdur == -1:
#                 # File reading was not successful. Delete file.
#                 self.report(f"Could not get file {_n}.")
#                 self.log_short_message(f"Could not get file {_n}.")
#                 try:
#                     os.remove(_fdetails.fullname)
#                     self.currfiles["nogot"].append(_fdetails.name)
#                 except Exception as e:
#                     pass
#             else:
#                 # Success. 
#                 _alldur += _tdur
#                 self.currfiles["got"].append(_fdetails.name)
#             self.currfiles["toget"].pop(0)
            
#             # Update all files details.
#             self.params["files"][self.sess_time_str] = self.currfiles
#             self._write_prg_params_file()
#             _n += 1
#         self.report(f"Done reading all files ({_alldur}).")
#         self.log_short_message(f"Done reading all files ({_alldur}).")
        
#         await self.take_a_break()        
#         await self._change_state_to(DockStnStates.WORK_FILEDEL)

#     def _init_file_to_get_details(self, n:int, N:int, fname:str) -> attrdict.AttrDict:
#         """Initializes an attribute dict with the details of the file to
#         be read from ARIMU."""
#         _fdet = attrdict.AttrDict()
#         _fdet.name = fname
#         _fdet.fullname = f"{self.sess_data_dir}{os.sep}{fname}"
#         _fdet.totalsz = 0
#         _fdet.currsz = 0
#         _fdet.n = n + 1
#         _fdet.N = N
#         return _fdet 
    
#     async def handle_working_filedelete(self):
#         """Handles the WORKING_FILEDEL state."""
#         # Get the list of all files.
#         _all_files = glob.glob(f"{self.sess_data_dir}{os.sep}*.bin")
#         _all_files = [_f for _f in _all_files
#                       if _f not in self.params["deleted"]]
#         # Get their time stamps.
#         _filedts = [
#             self.sess_time - dt.fromtimestamp(int(_f.split(".")[0].split("_")[-1])) 
#             for _f in _all_files
#         ]
#         _files_todel = [fname for i, fname in enumerate(_all_files)
#                         if _filedts[i] > tdel(days=10)]
#         _N = len(_files_todel)
#         _ndel = 0
#         # Go through files and delete the ones that are more than 10 days old.
#         for finx, fname in enumerate(_files_todel):
#             _fname = fname.split(os.sep)[-1]
#             (_, _st, _er, _pl) = await self.arimu.deletefile(_fname)
#             if _pl is not None:
#                 self._update_dev_state_error(_st, _er)
#                 if _pl == ArimuAdditionalFlags.FILEDELETED:
#                     _ndel += 1
#                     self.report(f"Deleted {_fname}.")
#                     self.log_short_message(f"Deleted file ({finx+1} / {_N})")
#                     self.params["deleted"].append(_fname)
#                     self._write_prg_params_file()
        
#         # All done. Change state to IDLE.
#         self.report(f"Deleted files ({_ndel}).")
#         self.log_short_message(f"Deleted files ({_ndel}).")
#         ArimuDocWorker.return_work_pass(self.comport)
#         await self._change_state_to(DockStnStates.WORK_RELAXNG)
    
#     async def handle_worker_idle(self):
#         """Handles the WORKER_IDLE state."""
#         await asyncio.sleep(5)
        
#     async def _get_write_time(self):
#         # log.info(self._logmsg("Getting ARIMU time."))
#         _, _st, _er, _pl = await self.arimu.gettime()
#         self.prg_params["setgettime"][self._now.strftime(DTSTRFMT)]["get"] = \
#             _pl[0].strftime(DTSTRFMT)
#         self._update_state_err(_st, _er)
#         self.log_response()

#     async def _set_write_dev_time(self):
#         _currt = dt.now()
#         while True:
#             _, _st, _er, _pl = await self.arimu.settime(dtvalue=_currt)
#             if _pl is not None:
#                 self._update_state_err(_st, _er)
#                 _msg = (f"Time set to [{_pl[0].strftime(DTSTRFMT)}] "
#                         + f"[{_pl[1]}us]")
#                 # log.info(self._logmsg(msg=_msg))
#                 break
#             await asyncio.sleep(self.regulardelay)
            
#         self.prg_params["setgettime"][self._now.strftime(DTSTRFMT)]["set"] = \
#             _pl[0].strftime(DTSTRFMT)
#         self._write_prg_params_file()
#         return _pl[0].strftime(DTSTRFMT)

#     async def _wait_and_connect(self):
#         """Function to wait for the serial port of interest, and connect to
#         the port."""
#         #
#         # Wait for the serial port.
#         if self._comfound is False:
#             self.report(f"Waiting for port {self.comport}")
#             self.log_short_message(f"Waiting for port {self.comport}")
#             _waiting = True
#             while _waiting:
#                 _cports = [p.name for p in comports()]
#                 _waiting = self.comport not in _cports
#                 await asyncio.sleep(ArimuDocWorker.CONNECT_WAIT_PERIOD)
#             self._comfound = True
#             self.report(f"Found port {self.comport}")
#             self.log_short_message(f"Found port {self.comport}")
#         #
#         # Connect to PORT.
#         try:
#             self.arimu = ArimuAsync(self.comport, baudrate=115200)
#             self.report(f"Connected to {self.comport}")
#             self.log_short_message(f"Connected to {self.comport}")
#         except Exception as e:
#             self.report(
#                 f"Error connecting to {self.comport}."
#                 + "Are you sure you've connected an ARIMU?"
#                 + "Details are given below."
#             )
#             self.log_short_message(
#                 f"Error connecting to {self.comport}. Device may not be ARIMU."
#             )
#             print("\n")
#             print(e)
#             traceback.print_exc()
#             return False
#         return True\
    
#     async def _get_device_name(self):
#         """Ping device and get device name."""
#         for i in range(ArimuDocWorker.MAX_CMD_RETRY_COUNT):
#             (_, _st, _er, _pl) = await self.arimu.ping()
#             if (_pl is not None
#                 and "ARIMU" in bytearray(_pl).decode()):
#                 self._update_dev_state_error(_st, _er)
#                 self.devname = bytearray(_pl).decode()
#                 self.report(f"Device name is {self.devname}",
#                             rtype=DockStnReports.OVERWRITE)
#                 self.log_short_message(f"Device name is {self.devname}",
#                                        rtype=DockStnReports.OVERWRITE)
#                 return True
#             await self.take_a_break()
#         # Did not get expected response.
#         self.report(
#             "Error ping to the device. "
#             + "Please make sure an ARIMU is connected."
#         )
#         return False
    
#     async def _get_device_time(self):
#         """Get device time."""
#         for i in range(ArimuDocWorker.MAX_CMD_RETRY_COUNT):
#             (_, _st, _er, _pl) = await self.arimu.gettime()
#             if _pl is not None:
#                 self._update_dev_state_error(_st, _er)
#                 self.params["setgettime"][self.sess_time_str] = \
#                     _pl[0].strftime(DTSTRFMT)
#                 self._write_prg_params_file()
#                 return True
#             await self.take_a_break()
#         # Did not get expected response.
#         self.report(
#             "Error getting device time. "
#             + "Please make sure an ARIMU is connected."
#         )
#         return False
    
#     async def _set_device_to_none_state(self):
#         """Set device to NONE state."""
#         for i in range(ArimuDocWorker.MAX_CMD_RETRY_COUNT):
#             (_, _st, _er, _pl) = await self.arimu.settonone()
#             if _pl is not None:
#                 self._update_dev_state_error(_st, _er)
#                 return True
#             await self.take_a_break()
#         # Did not get expected response.
#         self.report(
#             "Error setting device to NONE state. "
#             + "Please make sure an ARIMU is connected."
#         )
#         return False
    
#     async def _set_device_to_dockstncomm_state(self):
#         """Set device to DOKCSTNCOMM state."""
#         try:
#             for i in range(ArimuDocWorker.MAX_CMD_RETRY_COUNT):
#                 (_, _st, _er, _pl) = await self.arimu.startdockstncomm()
#                 self._update_dev_state_error(_st, _er)
#                 if _st == ArimuStates.DOCKSTNCOMM:
#                     return True
#                 await self.take_a_break()
#         except:
#             pass
#         # Did not get expected response.
#         self.report(
#             "Error setting device to DOCKSTNCOMM state. "
#             + "Please make sure an ARIMU is connected."
#         )
#         return False
    
#     async def _set_device_time(self, currt):
#         """Sets the time on the device to the given time currt."""
#         for i in range(ArimuDocWorker.MAX_CMD_RETRY_COUNT):
#             # Set to docking station mode.
#             currt = dt.now()
#             (_, _st, _er, _pl) = await self.arimu.settime(dtvalue=currt)
#             if (_pl is not None
#                 and (_pl[0] - currt) < tdel(seconds=1)):
#                 self._update_dev_state_error(_st, _er)
#                 return True
#             await self.take_a_break()
#         # Did not get expected response.
#         self.report(
#             "Error setting time on device. "
#             + "Please make sure an ARIMU is connected."
#         )
#         return False
    
#     async def _get_device_filelist(self):
#         """Gets the list of all files on the device."""
#         self.pausetimer = True
#         for i in range(ArimuDocWorker.MAX_CMD_RETRY_COUNT):
#             self.report(f"Getting device file list. [{0:03d}]")
#             self.log_short_message(f"Getting device file list. [{0:03d}]")
#             _temp = await self._get_file_list_for_loop()
#             if len(_temp) == 0:
#                 # Try again.
#                 continue
#             else:
#                 break
#         self.pausetimer = False
#         print(_temp)
#         return _temp

#     async def _get_file_list_for_loop(self):
#         """Calls the listfiles function of ARIMU to get the list of file."""
#         _temp = []
#         async for (_, _st, _er, _pl) in self.arimu.listfiles(timeout=ArimuDocWorker.ARIMU_FILELIST_TIMEOUT):
#             if _pl is not None:
#                 self._update_dev_state_error(_st, _er)
#                 _temp += _pl
#                 self.report(f"Getting device file list. [{len(_temp):03d}]",
#                             rtype=DockStnReports.OVERWRITE)
#                 self.log_short_message(
#                     f"Getting device file list. [{len(_temp):03d}]",
#                     rtype=DockStnReports.OVERWRITE
#                 )
#             else:
#                 _temp = []
#         return _temp
    
#     async def _get_write_filedata(self, fdetails:attrdict.AttrDict) -> float:
#         """Get data bytes from the file on device and write it to disk."""
#         self.pausetimer = True
#         # Progress bar.
#         prgbar = ProgressBar(params={'divs': 40,
#                                      'max_val': 255})
#         got_file = True
#         _strt = time.time()
#         with open(fdetails.fullname, "wb") as fhndl:
#             try:
#                 async for (_, _st, _er, _pl) in self.arimu.getfiledata(fdetails.name):
#                     if _pl is None:
#                         got_file = False
#                         break
#                     self._update_dev_state_error(_st, _er)
#                     _tdur = time.time() - _strt
#                     fdetails = self._parse_write_file_payload(
#                         fdetails=fdetails,
#                         payload=_pl,
#                         fhandle=fhndl,
#                         tdur=_tdur,
#                         prgbar=prgbar
#                     )
#                     await asyncio.sleep(0.01)
                
#                 # Check if the file reading for successful.
#                 if got_file:
#                     self.pausetimer = False
#                     return _tdur
#             except:
#                 pass
#         self.report(" Error getting/saving file.", rtype=DockStnReports.APPEND)
#         self.log_short_message(" Error getting/saving file.",
#                                rtype=DockStnReports.APPEND)
#         self.pausetimer = False
#         return -1

#     def _parse_write_file_payload(self, fdetails, payload, fhandle,
#                                   tdur, prgbar) -> attrdict.AttrDict:
#         """To parse the given payload, write to the file and update dispaly."""
#         if payload[0] == ArimuAdditionalFlags.FILEHEADER:
#             fdetails.totalsz = payload[1]
#             self.report("")
#             self.log_short_message("")
#         elif payload[0] == ArimuAdditionalFlags.FILECONTENT:
#             # Write to file.
#             fhandle.write(payload[2])
#             fdetails.currsz += len(payload[2])
#             # Update progress bar
#             _pbstr, _prcnt = prgbar.update(payload[1])
#             # Display string
#             _str = [f"[{fdetails.n:3d}/{fdetails.N:3d}]",
#                     f"|{_pbstr}|",
#                     f"[{_prcnt:6.2f}%]",
#                     f"[{fdetails.currsz/1024:7.1f}kB /",
#                     f"{fdetails.totalsz/1024:7.1f}kB]",
#                     f"[{tdur:5.1f} sec]"]
#             self.report(f"{' '.join(_str)}", rtype=DockStnReports.OVERWRITE)
#             self.log_short_message(
#                 f"{fdetails.n:3d}/{fdetails.N:3d} {_prcnt:6.2f}% {_pbstr}",
#                 rtype=DockStnReports.OVERWRITE
#             )
#         return fdetails
    
#     def _get_prev_files_list(self):
#         """Returns the list of previous files obtained and not obtained from
#         the device."""
#         _files_got = list(
#             itertools.chain(*[v["got"] for v in self.params["files"].values()])
#         )
#         _files_nogot = list(
#             itertools.chain(*[v["nogot"] for v in self.params["files"].values()])
#         )
#         return _files_got, _files_nogot

#     def _write_prg_params_file(self):
#         """Write program params to disk."""
#         with open(self.params_file, 'w') as fh:
#              json.dump(self.params, fh, indent=4)

#     def _logmsg_gui(self, msg, ovwrt=False):
#         if ovwrt:
#             self._gui_log_msgs[-1] = msg
#             return
#         # Append to messages.
#         self._gui_log_msgs.append(msg)
#         if len(self._gui_log_msgs) > self._log_msg_len:
#             self._gui_log_msgs.pop(0)
    
#     def _update_dev_state_error(self, state, err):
#         """Updates the value of ARIMU state and error in the object."""
#         self.arimu_state = state if state is not None else -1
#         self.arimu_err = err if err is not None else 0
    
#     @staticmethod
#     def get_err_str(err):
#         _errstr = [Error_Types1[i]
#                    for i, _b in enumerate(get_number_bits(err)[::-1])
#                    if _b == 1]
#         return f"{'|'.join(_errstr)}"


# def inform(payload):
#     print(bytearray(payload).decode())


if __name__ == '__main__':
    sys.stdout.write("\nARIMU Data Reader\n")
    sys.stdout.write("-----------------\n")
    
    app = QtWidgets.QApplication(sys.argv)

    arimuwrkr = ArimuDocWorker("COM16", "lala", "data")
    arimuwrkr.connect()
    
    sys.exit(app.exec_())
    
    # Read the  name of the subjects whose data is to be obtained.
    # subjname = input("Enter the name of the subject: ")
    # Initialize ARIMU reader.
    # Read the COM ports.
    # with open("comports.txt", "r") as fh:
    #     cports = fh.readlines()
    # cports = [cp.split("\n")[0] for cp in cports]
    
    # read the COM ports.
    # arimudoc1 = ArimuDocWorker(cports[0], subjname, "data", donotdelete=True)
    # arimudoc2 = ArimuDocWorker(cports[1], subjname, "data", donotdelete=True)
    
    # Asyncio Eventloop
    # loop = asyncio.get_event_loop()
    # tasks = [
    #     loop.create_task(arimudoc1.timer()),
    #     loop.create_task(arimudoc1.start()),
    #     loop.create_task(arimudoc2.timer()),
    #     loop.create_task(arimudoc2.start()),
    # ]
    # loop.run_until_complete(asyncio.wait(tasks))
    # loop.close()
