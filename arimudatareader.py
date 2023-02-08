"""Arimu Data Reader module for reading data from Arimu device(s).

Author: Sivakumar Balasubramanian
Date: 01 October 2022
email: siva82kb@gmail.com
"""

import glob
import itertools
import json
import sys
import threading
import attrdict
from datetime import datetime as dt
import enum
from pathlib import Path
import os
import struct
import time

from PyQt5.QtGui import QTextCursor
from PyQt5 import (
    QtWidgets,)
from PyQt5.QtCore import (
    pyqtSignal,
    QTimer,)
from PyQt5.QtWidgets import (
    QInputDialog,
)
from arimuworker import ArimuDocWorker

import qtjedi
from serial.tools.list_ports import comports

from arimu_dreader_ui import Ui_ArimuDataReader
import _arimuworker
from asyncarimu import ArimuAdditionalFlags
from asyncarimu import (ArimuAdditionalFlags,
                        ArimuCommands,
                        ArimuStates,
                        Error_Types1,
                        get_number_bits)
from misc import (ProgressBar,)

import logging
import logging.config
log = logging.getLogger(__name__)


class ArmuRecorderStates(enum.Enum):
    Start = 0
    FindingSensors = 1
    SensorsNotFound = 2
    SensorsNotSelected = 3
    WAITINGTOSTART = 4
    WaitingToRecordTask = 5
    RecordingTask = 6
    ALLDONE = 7


class DockStnReports(enum.Enum):
    NEW = 0
    APPEND = 1
    OVERWRITE = 2
    
    def __str__(self):
        return self.name


class ArimuDataReaderStates(enum.Enum):
    WAITINGTOSTART = 0
    CONNECTTODEVICE = 1
    GETFILELIST = 2
    READINGFILESSTART = 3
    READINGFILESLOGGING = 4
    DELETINGFILES = 5
    ALLDONE = 6


class ArimuDataReader(QtWidgets.QMainWindow, Ui_ArimuDataReader):
    """Main window of the ARIMU Data Reader.
    """
    # Watch dog time threshold
    WATCHDOG_THRESHOLD = 5
    close_signal = pyqtSignal()

    def __init__(self, *args, **kwargs) -> None:
        """View initializer."""
        super(ArimuDataReader, self).__init__(*args, **kwargs)
        self.setupUi(self)

        # Fix size.
        self.setFixedSize(self.geometry().width(),
                          self.geometry().height())

        # Set up console variables
        self._max_lines = 24
        self._console_text = []
        self.display_text("ARIMU Data Reader")
        self.display_text("-----------------")
        self.display_text("Please selecte ARIMUs to read data from.")
        
        # Status text
        self._statustext = ''
        self._datarate = 0

        # Search COM ports with ARIMUs connected.
        self._comports = []
        self._connected = False
        self.update_list_of_comports()

        # Data reader statemachine.
        self._state : ArimuDataReaderStates = ArimuDataReaderStates.WAITINGTOSTART
        self._setup_statehandlrs()

        # ARIMU workers to get the data.
        self.arimuwrkr = None
        self.outdir = "subjectdata"
        self.arimudata = {"allfiles": [],
                          "subjs": [],
                          "toget": [],
                          "got": [],
                          "notgot": [],
                          "currfilename": '',
                          "currfiledata": []}

        # ARIMU individual file reading flag.
        self._readingcurrfile = False

        # Attach callbacks
        self.list_comports.itemSelectionChanged.connect(self._callback_com_item_changed)
        self.btn_refresh_comports.clicked.connect(self._callback_refresh_comports)
        self.btn_start_data_reading.clicked.connect(self._callback_start_reading)

        # Update UI
        self.update_ui()

        # Populate the list of ARIMU devices.
        self._datetimer = QTimer()
        self._datetimer.timeout.connect(self._callback_datetimer)
        self._datetimer.start(1000)
        # A Timer that is activated when the data reading is in progress.
        self._watchdogcounter = 0
        self._data_read_progress_timer = QTimer()
        self._data_read_progress_timer.timeout.connect(self._callback_data_read_progress_timer)
        
        self.update_ui()

    def update_list_of_comports(self):
        # Clear the current list.
        self.list_comports.clear()
        for p in comports():
            # Found a COM port. Now check if this is 
            self.list_comports.addItem(p.name)

    def display_text(self, text, text_type=DockStnReports.NEW):
        if text_type == DockStnReports.NEW:
            self._console_text.append(text)
            if len(self._console_text) > self._max_lines:
                self._console_text.pop(0)
        elif text_type == DockStnReports.APPEND:
            self._console_text[-1] = self._console_text[-1] + text
        else:
            self._console_text[-1] = text

        # Update the console text.
        self.lbl_console.setText("\n".join(self._console_text))

    def status_text(self, text, text_type=DockStnReports.NEW):
        if text_type == DockStnReports.NEW:
            self._statustext = text
        else:
            self._statustext += text

        # Update the console text.
        self.lbl_status.setText(self._statustext)

    def update_ui(self):
        # Enable refrsh button.
        self.btn_refresh_comports.setEnabled(len(self._comports) == 0)

        # Enable start data reading buttons.
        self.btn_start_data_reading.setEnabled(
            self.list_comports.count() > 0 and
            len(self.list_comports.selectedItems()) > 0
        )

    def _callback_refresh_comports(self):
        self.update_list_of_comports()
        self.update_ui()

    def _callback_com_item_changed(self):
        self.update_ui()

    def _callback_datetimer(self):
        self.lbl_datetime.setText(dt.now().strftime("%A, %d. %B %Y %I:%M:%S%p"))

    def _callback_data_read_progress_timer(self):
        """Runs only when the data reading is in progress."""
        if self._state == ArimuDataReaderStates.READINGFILESLOGGING:
            # Check the watchdog counter
            self._watchdogcounter += 1
            if self._watchdogcounter == ArimuDataReader.WATCHDOG_THRESHOLD:
                self.status_text("WD: ON | ")
                # The watchdog has timed out. Stop the data reading.
                _str = f"> Getting {self.arimudata['currfilename']} ... Failed!"
                self.display_text(_str, text_type=DockStnReports.OVERWRITE)
                # Move read file to "got" and clear reading file flag.
                self.arimudata['notgot'].append(self.arimudata['currfilename'])
                self._readingcurrfile = False
            else:
                self.status_text("WD: OFF | ")
            
            # Update date rate
            self.status_text(f"{self._datarate / 1024:3.1f} kBps | ", text_type=DockStnReports.APPEND)
            self._datarate = 0
            
            # Check if current file is done.
            if self._readingcurrfile is False:
                # Call the file logging handler.
                self._data_read_progress_timer.stop()
                self._state_handlers[self._state]()

    def _callback_start_reading(self):
        # Get the list of COM ports.
        self._comports = [_it.text() for _it in self.list_comports.selectedItems()]

        # State the state machine for reading data.
        self._state = ArimuDataReaderStates.WAITINGTOSTART
        self._state_handlers[self._state]()
        self.update_ui()

    def _setup_statehandlrs(self):
        self._state_handlers = {
            ArimuDataReaderStates.WAITINGTOSTART: self._handle_waiting_to_start,
            ArimuDataReaderStates.CONNECTTODEVICE: self._handle_connect_to_device,
            ArimuDataReaderStates.READINGFILESSTART: self._handle_reading_files_start,
            ArimuDataReaderStates.READINGFILESLOGGING: self._handle_start_logging_files,
        }

    def _handle_arimuwrkr_connect_response(self, devname):
        self._state_handlers[self._state](devname)

    def _handle_arimuwrkr_filelist_response(self, filelist):
        # Check if the list is empty.
        if len(filelist) > 0:
            # Check if this is the first packet.
            self.arimudata['allfiles'] += tuple(filelist)
            self.display_text(f"> Gettting list of files. [{len(self.arimudata['allfiles']):3d}]",
                              text_type=DockStnReports.OVERWRITE)
        else:
            # Empty list of files. That marks the end of the response.
            # 1. Find the list of files with the 'data' in its name and with
            # the '.bin' extension.
            self.arimudata['allfiles'] = [
                _f for _f in self.arimudata['allfiles']
                if "data" in _f and ".bin" in _f
            ]

            # 2. Get subjects from the file list.
            self.arimudata['subjs'] = list(set([_f.split('_')[0] for _f in self.arimudata['allfiles']]))
            self.display_text(f"> Subjects found: {', '.join(self.arimudata['subjs'])}",
                              text_type=DockStnReports.NEW)
            
            # 3. Create subject directories.
            for _s in self.arimudata['subjs']:
                # Create subject folders if they do not exist.
                # Check if the directroy exits, else create it.
                Path(os.sep.join((self.outdir, _s))).mkdir(parents=True, exist_ok=True)

            # 3. Change state to start getting files for the different subjects.
            self._state = ArimuDataReaderStates.READINGFILESSTART
            self._state_handlers[self._state]()

    def _handle_arimuwrkr_filedata_response(self, filedata):
        # Check if its the file header
        self._watchdogcounter = 0
        if filedata[0] == ArimuAdditionalFlags.NOFILE:
            # The current file was not found. Skip the current file.
            pass
        elif filedata[0] == ArimuAdditionalFlags.FILEHEADER:
            # Header of the current file. Create a new file.
            pass
        elif filedata[0] == ArimuAdditionalFlags.FILECONTENT:
            # Content of the current file. Save file data.
            self.arimudata['currfiledata'] += filedata[1][1:]
            _filestoget = [_f[0] for _f in self.arimudata['toget'] if _f[1] is True]
            _str = " ".join((f"> Getting {self.arimudata['currfilename']}",
                            f"({100 * filedata[1][0] / 255:3.1f}%)",
                            f"[{len(_filestoget):3d} files left]"))
            self.display_text(_str, text_type=DockStnReports.OVERWRITE)
            # Numnber of bytes obtained.
            self._datarate += len(filedata[1][1:])
            # Check if this is the last packet.
            if filedata[1][0] == 255:
                # All data obtained. Write data to file.
                # Get subject name.
                _s = self.arimudata['currfilename'].split('_', maxsplit=1)[0]
                with open(os.sep.join((self.outdir, _s, self.arimudata['currfilename'])), 'wb') as _f:
                    _f.write(bytearray(self.arimudata['currfiledata']))
                _str = f"> Getting {self.arimudata['currfilename']} ... Done!"
                self.display_text(_str, text_type=DockStnReports.OVERWRITE)

                # Move read file to "got" and clear reading file flag.
                self.arimudata['got'].append(self.arimudata['currfilename'])
                self._readingcurrfile = False

    def _handle_start_logging_files(self):
        """Start logging data ready from the device.
        """
        # Get the next file.
        _toget = False
        while _toget is False and len(self.arimudata['toget']) > 0:
            _filename, _toget = self.arimudata['toget'].pop(0)
            
        # Check if there are still files to get.
        if len(self.arimudata['toget']) == 0:
            print("Got everything dude!")
            return
        
        # Get file from the device.
        self.display_text(f"> Getting {_filename}", text_type=DockStnReports.NEW)
        self.arimudata['currfilename'] = _filename
        self.arimudata['currfiledata'] = []
        self._readingcurrfile = True
        # Connect file data handler if it is not already connected.
        try:
            self.arimuwrkr.file_data.disconnect()
        except TypeError:
            pass
        self.arimuwrkr.file_data.connect(self._handle_arimuwrkr_filedata_response)
        self.arimuwrkr.get_file_data(_filename)

        # Start the data reading progress timer.
        self._data_read_progress_timer.start(1000)

    def _handle_reading_files_start(self):
        """Start reading files on the device. This functions generates the list
        of files that need to be read.
        """
        _toget = []
        for _s in self.arimudata['subjs']:
            # Get the list of files for this subject.
            _subjfiles = [_f for _f in self.arimudata['allfiles'] if _s == _f.split('_')[0]]
            # Existing files.
            _exstfiles = [_ef.split(os.sep)[-1]
                          for _ef in glob.glob(os.sep.join((self.outdir, _s, "*.bin")))]
            # Files to get
            _toget += [_f for _f in _subjfiles if _f not in _exstfiles]

        # Update the list of files to get.
        self.arimudata['toget'] = [
            (_f, _f in _toget)
            for _f in self.arimudata['allfiles']
        ]

        # Change state to start logging files.
        self._state = ArimuDataReaderStates.READINGFILESLOGGING
        self._state_handlers[self._state]()

    def _handle_waiting_to_start(self, *args):
        """Check if there are any devices from which data is to be read.
        """
        if len(self._comports) == 0:
            self._state = ArimuDataReaderStates.WAITINGTOSTART
            return
        # There are devices from which data is to be read.
        # Create a Arimu worker for this device.
        self.arimuwrkr = ArimuDocWorker(self._comports[0], "noone",
                                        "data", donotdelete=True)
        self.arimuwrkr.connect_response.connect(self._handle_arimuwrkr_connect_response)
        self.arimuwrkr.connect()
        self.display_text(f"> Connecting to {self._comports[0]}.")
        self._state = ArimuDataReaderStates.CONNECTTODEVICE
        
    def _handle_connect_to_device(self, *args):
        # Check if the device is an ARIMU device.
        if "ARIMU" in args[0]:
            self.display_text(f" Device is {args[0]}.", text_type=DockStnReports.APPEND)
            # self._state = ArimuDataReaderStates.GETFILELIST
            self.arimuwrkr.file_list.connect(self._handle_arimuwrkr_filelist_response)
            self.arimuwrkr.get_filelist()
            self.arimudata["allfiles"] = []
            self.arimudata["subjs"] = []
            self.arimudata["toget"] = []
            self.arimudata["got"] = []
            self.arimudata["notgot"] = []
            self.arimudata["currfilename"] = ''
            self.arimudata["currfiledata"] = []
            self.display_text("> Gettting list of files.")
    
    # ######################### #
    # Other supporting funftion #
    # ######################### #
    # def _organize_allfilist_into_subjlist(self):
    #     self.arimudata['subjs'] = list(set([
    #         _f.split('_')[0] for _f in self.arimudata['allfiles']
    #     ]))
    #     self.arimudata['subjfiles'] = {
    #         _s: [
    #             _f for _f in self.arimudata['allfiles']
    #             if _f.split('_')[0] == _s
    #         ]
    #         for _s in self.arimudata['subjs']
    #     }
        
    def _subjs_and_files(self):
        for _s, _sf in self.arimudata['subjfiles'].items():
            for _f in _sf:
                yield _s, _f
    
    def _get_data_files(self, filedetails, subj):
        # Display subject details
        self.display_text(f"> Subject: {subj} (To get: {len(filedetails['toget'])}).",
                          text_type=DockStnReports.NEW)
        time.sleep(0.1)
        # Go through all files and get them.
        _inx = 0
        self._readingcurrfile = False
        while True:
            # Check if the current file is still being read.
            if self._readingcurrfile:
                time.sleep(0.01)
                continue
            # Get the next file.
            _f = filedetails['toget'][_inx]
            self.display_text(f"> Getting {_f}.", text_type=DockStnReports.NEW)
            # self.arimuwrkr.file_list.connect(self._handle_arimuwrkr_filedata_response)
            # self.arimuwrkr.get_file_data(_f)
            # self.arimudata['subjfiles'][subj]['got'].append(_f)
            # self.display_text(f" Done.", text_type=DockStnReports.APPEND)

    
    #     # Arimu Client.
    #     self._comport = ""
    #     self._client = None
    #     self._fatal = False
    #     self._prgState = ArimuStates.NONE
    #     self._err = 0
    #     self._devname = ""
    #     self._subjname = ""
    #     self._currt = ""
    #     self._syst = ""
    #     self._currdevfname = ""
    #     self._pinging = False
    #     self._wait_for_info = {"subjname": 20,
    #                            "mode":\n1,
    #                            "currtime": 1,
    #                            "filename": 10,
    #                            "devname" : 100}
    #     self._updatecnt = 0
    #     self._statusdisp = False
        
    #     # File saving related variables.,
    #     self._flist = []
    #     self._flist_temp = []
    #     self._currfname = []
    #     self._currfiledetails = None
    #     self._strm_disp_cnt = 0
    #     self._dockstn_enable = False
        
    #     # stream logging.
    #     self._strm_fname = ""
    #     self._strm_fhndl = None
        
    #     # Welcome message
    #     self.display("Welcome to the Arimu Device Manager", False)
        
    #     # Get the list of ARIMU devices.
    #     self.update_list_of_comports()
        
    #     # ARIMU Response Handler.
    #     self._arimu_resp_hndlrs = {
    #         ArimuCommands.STATUS: self._handle_status_response,
    #         ArimuCommands.PING: self._handle_ping_response,
    #         ArimuCommands.LISTFILES: self._handle_listfiles_response,
    #         ArimuCommands.GETFILEDATA: self._handle_getfiledata_response,
    #         ArimuCommands.DELETEFILE: self._handle_deletefile_response,
    #         ArimuCommands.SETTIME: self._handle_settime_response,
    #         ArimuCommands.GETTIME: self._handle_gettime_response,
    #         ArimuCommands.STARTSTREAM: self._handle_start_stream_response,
    #         ArimuCommands.STOPSTREAM: self._handle_stop_stream_response,
    #         ArimuCommands.STARTDOCKSTNCOMM: self._handle_start_dockstncomm_response,
    #         ArimuCommands.STOPDOCKSTNCOMM: self._handle_stop_dockstncomm_response,
    #         ArimuCommands.SETSUBJECT: self._handle_setsubject_response,
    #         ArimuCommands.GETSUBJECT: self._handle_getsubject_response,
    #         ArimuCommands.CURRENTFILENAME: self._handle_currentfilename_response,
    #         ArimuCommands.STARTEXPT: self._handle_startexpt_response,
    #         ArimuCommands.STOPEXPT: self._handle_stopexpt_response,
    #         ArimuCommands.STARTNORMAL: self._handle_startnormal_response,
    #         ArimuCommands.STOPNORMAL: self._handle_stopnormal_response,
    #         ArimuCommands.SETTONONE: self._handle_settonone_response
    #     }
        
    #     # Attach callbacks.
    #     self.list_com_ports.itemSelectionChanged.connect(self._callback_com_item_changed)
    #     self.btn_refresh_com.clicked.connect(self._callback_refresh_comports)
    #     self.btn_connect_com.clicked.connect(self._callback_connect_to_arimu)
    #     self.btn_set_time.clicked.connect(self._callback_settime_arimu)
    #     self.btn_set_subjname.clicked.connect(self._callback_set_subjname_arimu)
    #     self.btn_get_files.clicked.connect(self._callback_get_files_arimu)
    #     self.btn_get_file_data.clicked.connect(self._callback_get_file_data_arimu)
        
    #     # Populate the list of ARIMU devices.
    #     self._timer = QTimer()
    #     self._timer.timeout.connect(self._callback_status_time)
    #     self._updatecnt = -1
    #     self._timer.start(500)
    #     self.update_ui()
    
    # @property
    # def connected(self):
    #     return (self._client is not None)
    
    # def display(self, msg, currtime=True):
    #     _headstr = (f"[{dt.now().strftime('%y/%m/%d %H:%M:%S')}] "
    #                 if currtime
    #                 else "" )
    #     self.text_console.appendPlainText(
    #         f"{_headstr} {msg}"
    #     )
    
    # def display_response(self, msg, currtime=True):
    #     self.text_console.appendPlainText(
    #         f"{msg}"
    #     )
    
    # def _display_error(self, err1, err2):
    #     # Display all errors.
    #     _errs = [Error_Types1[i]
    #              for i, _b in enumerate(get_number_bits(err1)[::-1])
    #              if _b == 1]
    #     self.display(f"Error: {' | '.join(_errs)}")
    
    # def update_list_of_comports(self):
    #     # Clear the current list.
    #     self.list_com_ports.clear()
    #     for p in comports():
    #         self.list_com_ports.addItem(p.name)
    
    # def update_ui(self):
    #     # Update State and Error.
    #     if self._err == 0x00:
    #         _errs = []
    #     else:
    #         _errs = [Error_Types1[i]
    #                  for i, _b in enumerate(get_number_bits(self._err)[::-1])
    #                  if _b == 1]

    #     if self.connected:
    #         self.list_com_ports.setEnabled(False)
    #         self.btn_connect_com.setText("Disconnect")
    #         self.btn_connect_com.setEnabled(True)
    #         # Update device details display.
    #         self.text_arimu_dev_details.setPlainText("\n".join((
    #             f"COM port : {self._comport}",
    #             f"Dev name : {self._devname}",
    #             f"Subject  : {self._subjname}",
    #             f"Dev Mode : {ArimuStates.state_name(self._prgState)}",
    #             f"Dev Err  : {' | '.join(_errs) if len(_errs) > 0 else 'No Errors'}",
    #             f"Sys time : {self._syst}",
    #             f"Dev time : {self._currt}",
    #             "",
    #             f"Dev file : {self._currdevfname}",
    #         )))
    #     else:
    #         self.list_com_ports.setEnabled(True)
    #         self.btn_connect_com.setText("Connect")
    #         # Enable/Disable connect button.
    #         self.btn_connect_com.setEnabled(
    #             self.list_com_ports.count() > 0 and
    #             self.list_com_ports.currentItem() is not None
    #         )
    #         self.text_arimu_dev_details.setPlainText("No device connected.")
        
    #     # Enable/disable all other controls
    #     self.btn_set_time.setEnabled(self.connected)
    #     self.btn_set_subjname.setEnabled(self.connected)
    #     self.btn_get_files.setEnabled(self.connected)
    #     self.btn_get_file_data.setEnabled(self.connected)
        
    #     # Enable ARIMU commands.
    #     self.btn_set_time.setEnabled(self.connected)
    #     self.btn_get_files.setEnabled(self.connected)
    #     self.btn_set_subjname.setEnabled(self.connected)
        
    #     # Check of the status lable must be cleared.
    #     if self._statusdisp is False:
    #         self.lbl_status.setText("")
    
    # def _callback_com_item_changed(self):
    #     self.update_ui()
    
    # def _callback_refresh_comports(self):
    #     self.update_list_of_comports()
    #     self.update_ui()
    
    # def _callback_connect_to_arimu(self):
    #     if self.connected is False:
    #         self._comport = self.list_com_ports.currentItem().text()
    #         self._client = qtjedi.JediComm(self._comport, 115200)
    #         self._client.newdata_signal.connect(self._handle_new_packets)
    #         self._client.start()
    #         time.sleep(1.0)
    #         # Get the status of the device.
    #         self._client.send_message([ArimuCommands.STATUS])
    #         # Start pinging.
    #         self._pinging = True
    #     else:
    #         self._client.abort()
    #         self._client.disconnect()
    #         self._comport = ""
    #         self._client = None
    #     self.update_ui()
    
    # def _callback_status_time(self):
    #     if not self.connected:
    #         return
        
    #     self._updatecnt += 1
    #     # Get current time
    #     if self._updatecnt % self._wait_for_info["devname"] == 0:
    #         self._client.send_message([ArimuCommands.PING])
    #     if self._updatecnt % self._wait_for_info["currtime"] == 0:
    #         # Set system time
    #         self._syst = dt.now().strftime('%y/%m/%d %H:%M:%S.%f')[:-4]
    #         self._client.send_message([ArimuCommands.GETTIME])
    #     if self._updatecnt % self._wait_for_info["subjname"] == 0:
    #         self._client.send_message([ArimuCommands.GETSUBJECT])
    #     if self._updatecnt % self._wait_for_info["filename"] == 0:
    #         self._client.send_message([ArimuCommands.CURRENTFILENAME])
    #     self.update_ui()
    
    # def _handle_new_packets(self, payload):
    #     # Handle packet.
    #     _cmd, self._prgState, self._err, *_pl = payload
    #     self._arimu_resp_hndlrs[_cmd](_pl)
    #     self.update_ui()
    
    # def _handle_status_response(self, payload):
    #     self.update_ui()
            
    # def _handle_ping_response(self, payload):
    #     self._devname = bytearray(payload).decode()
    
    # def _handle_gettime_response(self, payload):
    #     _pldbytes = [bytearray(payload[i:i+4])
    #                  for i in range(0, 28, 4)]
    #     # Group payload components.
    #     _temp = [struct.unpack('<L', _pldbytes[i])[-1]
    #              for i in range(7)]
    #     _ts = (f'{_temp[0]:02d}/{_temp[1]:02d}/{_temp[2]:02d}'
    #            + f' {_temp[3]:02d}:{_temp[4]:02d}:{_temp[5]:02d}.{_temp[6]:02d}')
    #     self._currt = _ts
    
    # def _handle_settime_response(self, payload):
    #     # First set the device in the DockingStationMode.
        
    #     _pldbytes = [bytearray(payload[i:i+4])
    #                  for i in range(0, 28, 4)]
    #     # Group payload components.
    #     _temp = [struct.unpack('<L', _pldbytes[i])[-1]
    #              for i in range(7)]
    #     _ts = (f'{_temp[0]:02d}-{_temp[1]:02d}-{_temp[2]:02d}'
    #            + f'T{_temp[3]}:{_temp[4]}:{_temp[5]}.{_temp[6]}')
    #     _currt = dt.strptime(_ts, '%y-%m-%dT%H:%M:%S.%f')
    #     # Micros data.
    #     _microst = struct.unpack('<L', bytearray(payload[28:32]))[-1]
    #     self.display_response(f"Current time: {_currt} | Micros: {_microst} us")
    
    # def _handle_setsubject_response(self, payload):
    #     self.display_response(f"Current subject: {bytearray(payload).decode()}")
        
    # def _handle_getsubject_response(self, payload):
    #     self._subjname = bytearray(payload).decode()
    
    # def _handle_currentfilename_response(self, payload):
    #     self._currdevfname = bytearray(payload).decode()
    
    # def _handle_listfiles_response(self, payload):
    #     # Decode nad build file list.
    #     # 1. check if this is the start of file list.
    #     _str = bytearray(payload).decode()
    #     if _str[0] == '[':
    #         # Create a new list.
    #         self._flist = []
    #         self._flist_temp = bytearray(payload).decode()[1:-1].split(",")
    #     elif len(self._flist) == 0 and len(self._flist_temp) != 0:
    #         # Check if end of list is reached.
    #         if _str[-1] == ']':
    #             # End of file list.
    #             self._flist_temp += bytearray(payload).decode()[0:-2].split(",")
    #             self._flist = self._flist_temp
    #             self._flist_temp = []
    #         else:
    #             self._flist_temp += bytearray(payload).decode()[0:-1].split(",")
    #     if len(self._flist) != 0:
    #         self.display_response(f"List of fisles ({len(self._flist)}):\n{' | '.join(self._flist)}")
    
    # def _init_file_to_get_details(self, fname:str) -> attrdict.AttrDict:
    #     """Initializes an attribute dict with the details of the file to
    #     be read from ARIMU."""
    #     _fdet = attrdict.AttrDict()
    #     _fdet.name = fname
    #     _fdet.handle = open(f"data/temporary/{_fdet.name}", "wb")
    #     _fdet.totalsz = 0
    #     _fdet.currsz = 0
    #     _fdet.data = []
    #     _fdet.prgbar = ProgressBar(params={'divs': 20,
    #                                        'max_val': 255})
    #     return _fdet 
    
    # def _handle_getfiledata_response(self, payload):
    #     if payload[0] == ArimuAdditionalFlags.NOFILE:
    #         self.display_response("No such file.")
    #     elif payload[0] == ArimuAdditionalFlags.FILEHEADER:
    #         self._currfiledetails = self._init_file_to_get_details(self._currfname)
    #         self._currfiledetails.totalsz = struct.unpack('<L', bytearray(payload[1:5]))[0]
    #         self._statusdisp = True
    #         self.lbl_status.setText(
    #             "File header received. File size: "
    #             + f"{self._currfiledetails.totalsz/1024.:8.2f}kB."
    #         )
    #     elif payload[0] == ArimuAdditionalFlags.FILECONTENT:
    #         # Write to file.
    #         self._currfiledetails.currsz += len(payload[2:])
    #         # Update progress bar
    #         _pbstr, _prcnt = self._currfiledetails.prgbar.update(payload[1])
    #         self._currfiledetails.handle.write(bytearray(payload[2:]))
    #         # Display string
    #         _str = [f"|{_pbstr}|",
    #                 f"[{_prcnt:6.2f}%]",
    #                 f"[{self._currfiledetails.currsz/1024:8.2f}kB /",
    #                 f"{self._currfiledetails.totalsz/1024:8.2f}kB]",]
    #         self.lbl_status.setText(f"{' '.join(_str)}")
    #         # Check if the file has been obtained.
    #         if _prcnt >= 100:
    #             self._statusdisp = False
    #             self._currfiledetails.handle
    #             self.display_response(f"File data reading done! File {self._currfiledetails.name} saved!")
    
    # def _handle_deletefile_response(self, payload):
    #     if payload[0] == ArimuAdditionalFlags.FILEDELETED:
    #         self.display_response(f"File {self._currfname} deleted!")
    #     if payload[0] == ArimuAdditionalFlags.FILENOTDELETED:
    #         self.display_response(f"File {self._currfname} not deleted!")
            
    # def _handle_start_stream_response(self, payload):
    #     self._strm_disp_cnt += 1
    #     # Decode data and display on the streaming strip.
    #     if len(payload) == 20:
    #         _epoch = struct.unpack('<L', bytearray(payload[0:4]))[0]
    #         _micros = struct.unpack('<L', bytearray(payload[4:8]))[0]
    #         _imu = struct.unpack('<6h', bytearray(payload[8:20]))
    #         # Write row.
    #         if self._strm_fhndl is not None:
    #             _str = ",".join((f"{_epoch}",
    #                              f"{_micros}",
    #                              ",".join(map(str, _imu))))
    #             self._strm_fhndl.write(f"{_str}\n")
    #         if self._strm_disp_cnt % 10 == 0:
    #             _str = f"{_micros // 1000:06d} | acc: ({_imu[0]:+6d}, {_imu[1]:+6d}, {_imu[2]:+6d})"
    #             _str += f" | gyr: ({_imu[3]:+6d}, {_imu[4]:+6d}, {_imu[5]:+6d})"
    #             self.lbl_stream.setText(_str)
    
    # def _handle_stop_stream_response(self, payload):
    #     # Close stream file
    #     if self._strm_fhndl is not None:
    #         self._strm_fhndl.close()
    #         self._strm_fhndl = None
    #     self.lbl_stream.setText("")
    
    # def _handle_startnormal_response(self, payload):
    #     self.display_response("Started Normal Mode.")

    # def _handle_stopnormal_response(self, payload):
    #     self.display_response("Stopped Normal Mode.")

    # def _handle_startexpt_response(self, payload):
    #     self.display_response("Started Experiment Mode")
        
    # def _handle_stopexpt_response(self, payload):
    #     self.display_response("Stopped Experiment Mode")
    
    # def _handle_start_dockstncomm_response(self, payload):
    #     self.display_response("Started Docking Station Communication Mode.")
        
    # def _handle_stop_dockstncomm_response(self, payload):
    #     self.display_response("Termianted Docking Station Communication Mode.")
    
    # def _handle_settonone_response(self, payload):
    #     self.display_response("Set to None Mode.")

    # def _callback_ping_arimu(self):
    #     # Send ArimuCommands.PING message to ARIMU
    #     self.display("Pinging ARIMU ... ")
    #     self._client.send_message([ArimuCommands.PING])
    
    # def _callback_gettime_arimu(self):
    #     # Get time
    #     self.display("Getting time ... ")
    #     self._client.send_message([ArimuCommands.GETTIME])
    
    # def _callback_settime_arimu(self):
    #     # Set the device in the docking station mode.
    #     self._client.send_message([ArimuCommands.STARTDOCKSTNCOMM])
    #     time.sleep(0.5)
    #     # Send time.
    #     _currt = dt.now()
    #     self.display(f"Setting time to {_currt.strftime('%y/%m/%d %H:%M:%S.%f')}")
    #     _dtvals = (struct.pack("<L", _currt.year % 100)
    #                + struct.pack("<L", _currt.month)
    #                + struct.pack("<L", _currt.day)
    #                + struct.pack("<L", _currt.hour)
    #                + struct.pack("<L", _currt.minute)
    #                + struct.pack("<L", _currt.second)
    #                + struct.pack("<L", _currt.microsecond // 10000))
    #     self._client.send_message(bytearray([ArimuCommands.SETTIME]) + _dtvals)
    
    # def _callback_get_subjname_arimu(self):
    #     self.display("Get Subject Name ... ")
    #     self._client.send_message([ArimuCommands.GETSUBJECT])
    
    # def _callback_set_subjname_arimu(self):
    #     self.display("Set Subject Name ... ")
    #     text, ok = QInputDialog.getText(self, 'Subject Name', 'Enter subjecty name:')
    #     if ok:
    #         # Set the device in the docking station mode.
    #         self._client.send_message([ArimuCommands.STARTDOCKSTNCOMM])
    #         time.sleep(0.5)    
    #         self._client.send_message(bytearray([ArimuCommands.SETSUBJECT])
    #                                   + bytearray(text, "ascii")
    #                                   + bytearray([0]))
    
    # def _callback_set_currentfilename_arimu(self):
    #     self.display("Get Current Data Filename ... ")
    #     self._client.send_message([ArimuCommands.CURRENTFILENAME])
    
    # def _callback_get_files_arimu(self):
    #     # Set the device in the docking station mode.
    #     self._client.send_message([ArimuCommands.STARTDOCKSTNCOMM])
    #     time.sleep(0.5)   
    #     self.display("Get list of files ... ")
    #     self._client.send_message([ArimuCommands.LISTFILES])
    
    # def _callback_get_file_data_arimu(self):
    #     _file, ok = QInputDialog.getItem(self, "Which file?", 
    #                                      "Select file: ", self._flist,
    #                                      0, False)
    #     if ok:
    #         # Set the device in the docking station mode.
    #         self._client.send_message([ArimuCommands.STARTDOCKSTNCOMM])
    #         time.sleep(0.5) 
    #         self._currfname = _file            
    #         self.display(f"Get file data ... {self._currfname}")
    #         self._client.send_message(bytearray([ArimuCommands.GETFILEDATA])
    #                                 + bytearray(self._currfname, "ascii")
    #                                 + bytearray([0]))

    # def _callback_delete_file_arimu(self):
    #     _file, ok = QInputDialog.getItem(self, "Which file?", 
    #                                      "Select file: ", self._flist,
    #                                      0, False)
    #     if ok:                        
    #         self._currfname = _file
    #         self.display(f"Delete file ... {self._currfname}")
    #         self._client.send_message(bytearray([ArimuCommands.DELETEFILE])
    #                                   + bytearray(self._currfname, "ascii")
    #                                   + bytearray([0]))
    
    # def _callback_start_stop_normal_arimu(self):
    #     # Check the current status.
    #     if self.btn_start_stop_normal.text() == "Start Normal":
    #         self.display("Starting Normal Mode ...")
    #         self._client.send_message([ArimuCommands.STARTNORMAL])
    #     else:
    #         self.display("Stopping Normal Mode ...")
    #         self._client.send_message([ArimuCommands.STOPNORMAL])
        
    # def _callback_start_stop_expt_arimu(self):
    #     # Check the current status.
    #     if self.btn_start_stop_expt.text() == "Start Experiment":
    #         self.display("Starting Experiment Mode ...")
    #         self._client.send_message([ArimuCommands.STARTEXPT])
    #     else:
    #         self.display("Stopping Experiment Mode ...")
    #         self._client.send_message([ArimuCommands.STOPEXPT])
        
    # def _callback_start_stop_strm_arimu(self):
    #     # Check the current status.
    #     if self.btn_start_stop_stream.text() == "Start Streaming":
    #         self.display("Starting Streaming Mode ...")
    #         self._client.send_message([ArimuCommands.STARTSTREAM])
    #         self._strm_disp_cnt = 0
    #         # open file.
    #         self._strm_fname = f"streamdata/stream_data_{dt.now().strftime('%y_%m_%d_%H_%M_%S')}.csv"
    #         self._strm_fhndl = open(self._strm_fname, "w")
    #         self._strm_fhndl.write("epoch,micros,ax,ay,az,gx,gy,gz\n")
    #     else:
    #         self.display("Stopping Streaming Mode ...")
    #         self._client.send_message([ArimuCommands.STOPSTREAM])

    # def _callback_dockstn_selected_arimu(self):
    #     # Check the current state.
    #     if self.gb_arimu_dockstn.isChecked():
    #         # Swtich on docking station mode.
    #         self.display("Starting Docking Station Communication Mode ...")
    #         self._client.send_message([ArimuCommands.STARTDOCKSTNCOMM])
    #     else:
    #         # Switch off docking station mode.
    #         self.display("Terminating Docking Station Communication Mode ...")
    #         self._client.send_message([ArimuCommands.STOPDOCKSTNCOMM])
    
    def closeEvent(self,event):
        self.close_signal.emit()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    mywin = ArimuDataReader()
    # ImageUpdate()
    mywin.show()
    sys.exit(app.exec_())