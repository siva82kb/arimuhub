"""Arimu Data Reader module for reading data from Arimu device(s).

Author: Sivakumar Balasubramanian
Date: 01 October 2022
email: siva82kb@gmail.com
"""

import glob
import sys
from datetime import datetime as dt
from datetime import timedelta as tdelta
import enum
from pathlib import Path
import os
import time

# from PyQt5.QtGui import QTextCursor
from PyQt5 import (
    QtWidgets,)
from PyQt5.QtCore import (
    pyqtSignal,
    QTimer,)
# from PyQt5.QtWidgets import (
#     QInputDialog,
# )
from arimuworker import ArimuDocWorker

# import qtjedi
from serial.tools.list_ports import comports

from arimu_dreader_ui import Ui_ArimuDataReader
# import _arimuworker
from asyncarimu import ArimuAdditionalFlags
from asyncarimu import (ArimuAdditionalFlags,)
# from misc import (ProgressBar,)

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
        self._comportinx = 0
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
                          "currfiledata": [],
                          "filestodelete": None}

        # ARIMU individual file reading flag.
        self._readingcurrfile = False

        # Attach callbacks
        self.list_comports.itemSelectionChanged.connect(self._callback_com_item_changed)
        self.btn_refresh_comports.clicked.connect(self._callback_refresh_comports)
        self.btn_start_data_reading.clicked.connect(self._callback_start_reading)

        # Variables for setting time on the devices after getting the data.
        # ARIMU workers to set the time on the devices.
        self._timesetwrkrs = [] 

        # Populate the list of ARIMU devices.
        self._datetimer = QTimer()
        self._datetimer.timeout.connect(self._callback_datetimer)
        self._datetimer.start(1000)
        # A Timer that is activated when the data reading is in progress.
        self._watchdogcounter = 0
        self._data_read_progress_timer = QTimer()
        self._data_read_progress_timer.timeout.connect(self._callback_data_read_progress_timer)
        # A Timer for setting time on the watches.
        self._time_setter_timer = QTimer()
        self._time_setter_timer.timeout.connect(self._callback_time_setter_timer)
        
        # Update UI
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
        print(self._comports)
        # Enable refrsh button.
        self.btn_refresh_comports.setEnabled(len(self._comports) == 0)

        # Enable start data reading buttons.
        self.btn_start_data_reading.setEnabled(
            self.list_comports.count() > 0 and
            len(self.list_comports.selectedItems()) > 0
        )
        
        # If device is connected, then disable the list of COM ports.
        if self._state != ArimuDataReaderStates.WAITINGTOSTART:
            self.list_comports.setEnabled(False)
            self.btn_refresh_comports.setEnabled(False)
            self.btn_start_data_reading.setEnabled(False)

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
    
    def _callback_time_setter_timer(self):
        """Runs when all data has been obtained. to regularly set the time on the watches.
        """
        if self._state == ArimuDataReaderStates.ALLDONE:
            # Go through the different compots, connect to them and set the time.
            _nowstr = dt.now().strftime('%d/%m/%y %H:%M:%S.%f')
            self.display_text(f"> Setting time to {_nowstr} on ",
                              text_type=DockStnReports.OVERWRITE)
            for i, _com in enumerate(self._comports):
                self._timesetwrkrs[i].set_time()
                self.display_text(f"{_com} ", text_type=DockStnReports.APPEND)

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
            ArimuDataReaderStates.DELETINGFILES: self._handle_deleting_files,
            ArimuDataReaderStates.ALLDONE: self._handle_all_done,
        }

    def _handle_arimuwrkr_connect_response(self, devname):
        self._state = ArimuDataReaderStates.CONNECTTODEVICE
        self._state_handlers[self._state](devname)

    def _handle_arimuwrkr_filelist_response(self, filelist):
        # Check if the list is empty.
        if len(filelist) > 0:
            # Check if this is the first packet.
            self.arimudata['allfiles'] += tuple(filelist[0])
            self.display_text(f"> Gettting list of files. [{len(self.arimudata['allfiles']):3d}]",
                              text_type=DockStnReports.OVERWRITE)
        else:
            # Check if there are files from the device.
            if len(self.arimudata['allfiles']) == 0:
                self.display_text("> No files to be read.", text_type=DockStnReports.NEW)
                 # Change state to start getting files for the different subjects.
                self._state = ArimuDataReaderStates.ALLDONE
                self._state_handlers[self._state]()
                return
            
            # There are files to be read.
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

    def _handle_arimuwrkr_filedelete_response(self):
        # Check if all files are done.
        if len(self.arimudata['filestodelete']) == 0:
            self.display_text("Done deleting old files!", text_type=DockStnReports.NEW)
            return

        # More files to delete.
        self._state_handlers[self._state]()

    def _handle_all_done(self):
        """All done with reading files.
        """
        # Disconnect the current device.
        self.arimuwrkr.disconnect()
        # Clear all other variables.
        self.arimudata["allfiles"] = []
        self.arimudata["subjs"] = []
        self.arimudata["toget"] = []
        self.arimudata["got"] = []
        self.arimudata["notgot"] = []
        self.arimudata["currfilename"] = ''
        self.arimudata["currfiledata"] = []
        self.arimudata["filestodelete"] = None

        # Get to the next comport.
        self._comportinx += 1
        # Check if all comports have been handled.
        if self._comportinx >= len(self._comports) :
            self.display_text("> Done with all devices!")
            #
            # Set time till the devices are removed.
            for _com in self._comports:
                self._timesetwrkrs.append(
                    ArimuDocWorker(_com, "noone", "data", donotdelete=True)
                )
                self._timesetwrkrs[-1].connect()
                self._timesetwrkrs[-1].set_time()
            self.display_text(f"> Setting time to {dt.now().strftime('%d/%m/%y %H:%M:%S.%f')}", text_type=DockStnReports.NEW)
            # Start time for regular time setting
            self._time_setter_timer.start(1000)
            return

        # More devices left.
        self._state = ArimuDataReaderStates.WAITINGTOSTART
        self._state_handlers[self._state]()

    def _handle_deleting_files(self):
        """Deleting old files on the device.
        """
        # Check if this is the first call to the function.
        if self.arimudata['filestodelete'] is None:
            self.display_text("> Looking for files to delete ... ", text_type=DockStnReports.NEW)
            _today = dt.now()
            _filedates = [(_f, dt.fromtimestamp(int(_f.split('_')[-1].split('.')[0])))
                        for _f in self.arimudata['allfiles']]
            self.arimudata['filestodelete'] = [_fd[0] for _fd in _filedates
                                            if (_today - _fd[1]) > tdelta(days=7)]
            self.arimuwrkr.file_delete.connect(self._handle_arimuwrkr_filedelete_response)
            self.display_text(f"found {len(self.arimudata['filestodelete'])}.", text_type=DockStnReports.APPEND)

        # Check if there are more files to be deleted.
        if len(self.arimudata['filestodelete']) == 0:
            self.display_text("> Done deleting old files!", text_type=DockStnReports.NEW)
            # Change state to all done.
            self._state = ArimuDataReaderStates.ALLDONE
            self._state_handlers[self._state]()
            return
        
        # There are files to delete.
        _nextfile = self.arimudata['filestodelete'].pop(0)
        self.arimuwrkr.delete_file(_nextfile)

    def _handle_start_logging_files(self):
        """Start logging data ready from the device.
        """
        # Get the next file.
        _toget = False
        while _toget is False and len(self.arimudata['toget']) > 0:
            _filename, _toget = self.arimudata['toget'].pop(0)

        # Check if there are still files to get.
        if len(self.arimudata['toget']) == 0:
            self.display_text("> Got all files!", text_type=DockStnReports.NEW)

            # Change state to deleting files.
            self._state = ArimuDataReaderStates.DELETINGFILES
            self._state_handlers[self._state]()
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
        if self._comportinx == len(self._comports):
            self._state = ArimuDataReaderStates.WAITINGTOSTART
            return
        # There are devices from which data is to be read.
        # Create a Arimu worker for this device.
        self.arimuwrkr = ArimuDocWorker(self._comports[self._comportinx], "noone",
                                        "data", donotdelete=True)
        self.arimuwrkr.connect_response.connect(self._handle_arimuwrkr_connect_response)
        self.arimuwrkr.connect()
        self.display_text(f"> Connecting to {self._comports[self._comportinx]}.")

    def _handle_connect_to_device(self, *args):
        # Check if the device is an ARIMU device.
        if "ARIMU" in args[0]:
            self.display_text(f" Device is {args[0]}.", text_type=DockStnReports.APPEND)
            # Get file list.
            # Clear variables.
            self.arimudata["allfiles"] = []
            self.arimudata["subjs"] = []
            self.arimudata["toget"] = []
            self.arimudata["got"] = []
            self.arimudata["notgot"] = []
            self.arimudata["currfilename"] = ''
            self.arimudata["currfiledata"] = []
            self.arimudata["filestodelete"] = None
            # Get files
            self.arimuwrkr.file_list.connect(self._handle_arimuwrkr_filelist_response)
            self.arimuwrkr.get_filelist()
            self.display_text("> Gettting list of files.")

            # update UI
            self.update_ui()

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

    def closeEvent(self, event):
        self.close_signal.emit()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    mywin = ArimuDataReader()
    # ImageUpdate()
    mywin.show()
    sys.exit(app.exec_())