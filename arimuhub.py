"""ArimuHub is the single stop solution for interacting with Arimu wearables
developed by yhe BioRehab Group for wearable movement monitoring applications.  

Author: Sivakumar Balasubramanian
Date: 24 Sept 2022
email: siva82kb@gmail.com
"""

import sys
from PyQt5 import (
    QtWidgets,)
from PyQt5.QtWidgets import (
    QMessageBox,
    QDesktopWidget
)

from arimu_hub_ui import Ui_ArimuHub

from arimudevmanager import ArimuDeviceManager
from arimudatareader import ArimuDataReader

class ArimuHub(QtWidgets.QMainWindow, Ui_ArimuHub):
    """Main window of the ArimuHub.
    """
    
    def __init__(self, *args, **kwargs) -> None:
        """View initializer."""
        super(ArimuHub, self).__init__(*args, **kwargs)
        self.setupUi(self)
        
        # Set at a reasonable location on the top left cornder.
        self.set_at_reasonable_location_on_the_screen()
        
        # Current window.
        self.currwin = None
        
        # Attach callbacks.
        self.btn_dev_manager.clicked.connect(self._callback_dev_manager)
        self.btn_data_reader.clicked.connect(self._callback_data_reader)
        self.btn_streaming.clicked.connect(self._callback_streaming)
        self.btn_about.clicked.connect(self._callback_about)
        
        # Update UI
        self.update_ui()
    
    def set_at_reasonable_location_on_the_screen(self):
        sg = QDesktopWidget().screenGeometry()
        x = sg.width() // 15
        y = sg.height() // 15
        self.move(x, y)
    
    def update_ui(self):
        # self.btn_about.setEnabled(self.currwin is None)
        self.btn_about.setEnabled(False)
        self.btn_data_reader.setEnabled(self.currwin is None)
        self.btn_dev_manager.setEnabled(self.currwin is None)
        # self.btn_streaming.setEnabled(self.currwin is None)
        self.btn_streaming.setEnabled(False)

    def _callback_dev_manager(self):
        if self.currwin is None:
            # Start webcam viewer
            self.currwin = ArimuDeviceManager()
            # Attach close call back function.
            self.currwin.close_signal.connect(self._callback_dev_manager_close)
            self.currwin.show()
        self.update_ui()

    def _callback_data_reader(self):
        if self.currwin is None:
            # Start webcam viewer
            self.currwin = ArimuDataReader()
            # Attach close call back function.
            self.currwin.close_signal.connect(self._callback_dev_manager_close)
            self.currwin.show()
        self.update_ui()

    def _callback_streaming(self):
        self.update_ui()

    def _callback_about(self):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText(
            "ArimuHub is used for managing and interacting with Arimu device. " + 
            "\n Developed by the BioRehab Group, CMC Vellore, India."
        )
        msgBox.setWindowTitle("About ArimuHub")
        msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

        returnValue = msgBox.exec()
        if returnValue == QMessageBox.Ok:
            print('OK clicked')
    
    def _callback_dev_manager_close(self):
        self.currwin = None
        self.update_ui()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    mywin = ArimuHub()
    mywin.show()
    sys.exit(app.exec_())