# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/arimu_viewer.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_ARIMUViewer(object):
    def setupUi(self, ARIMUViewer):
        ARIMUViewer.setObjectName("ARIMUViewer")
        ARIMUViewer.resize(721, 547)
        ARIMUViewer.setStatusTip("")
        self.centralwidget = QtWidgets.QWidget(ARIMUViewer)
        self.centralwidget.setObjectName("centralwidget")
        self.gb_arimu_commands = QtWidgets.QGroupBox(self.centralwidget)
        self.gb_arimu_commands.setGeometry(QtCore.QRect(10, 90, 151, 231))
        self.gb_arimu_commands.setObjectName("gb_arimu_commands")
        self.layoutWidget = QtWidgets.QWidget(self.gb_arimu_commands)
        self.layoutWidget.setGeometry(QtCore.QRect(10, 20, 131, 199))
        self.layoutWidget.setObjectName("layoutWidget")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.layoutWidget)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.btn_ping = QtWidgets.QPushButton(self.layoutWidget)
        self.btn_ping.setObjectName("btn_ping")
        self.verticalLayout_2.addWidget(self.btn_ping)
        self.btn_get_current_filename = QtWidgets.QPushButton(self.layoutWidget)
        self.btn_get_current_filename.setObjectName("btn_get_current_filename")
        self.verticalLayout_2.addWidget(self.btn_get_current_filename)
        self.btn_get_time = QtWidgets.QPushButton(self.layoutWidget)
        self.btn_get_time.setObjectName("btn_get_time")
        self.verticalLayout_2.addWidget(self.btn_get_time)
        self.btn_get_subjname = QtWidgets.QPushButton(self.layoutWidget)
        self.btn_get_subjname.setObjectName("btn_get_subjname")
        self.verticalLayout_2.addWidget(self.btn_get_subjname)
        self.btn_start_stop_normal = QtWidgets.QPushButton(self.layoutWidget)
        self.btn_start_stop_normal.setObjectName("btn_start_stop_normal")
        self.verticalLayout_2.addWidget(self.btn_start_stop_normal)
        self.btn_start_stop_expt = QtWidgets.QPushButton(self.layoutWidget)
        self.btn_start_stop_expt.setObjectName("btn_start_stop_expt")
        self.verticalLayout_2.addWidget(self.btn_start_stop_expt)
        self.btn_start_stop_stream = QtWidgets.QPushButton(self.layoutWidget)
        self.btn_start_stop_stream.setObjectName("btn_start_stop_stream")
        self.verticalLayout_2.addWidget(self.btn_start_stop_stream)
        self.layoutWidget1 = QtWidgets.QWidget(self.centralwidget)
        self.layoutWidget1.setGeometry(QtCore.QRect(11, 12, 151, 70))
        self.layoutWidget1.setObjectName("layoutWidget1")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.layoutWidget1)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(self.layoutWidget1)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.cb_com_devices = QtWidgets.QComboBox(self.layoutWidget1)
        self.cb_com_devices.setObjectName("cb_com_devices")
        self.verticalLayout.addWidget(self.cb_com_devices)
        self.btn_connect_com = QtWidgets.QPushButton(self.layoutWidget1)
        self.btn_connect_com.setObjectName("btn_connect_com")
        self.verticalLayout.addWidget(self.btn_connect_com)
        self.layoutWidget2 = QtWidgets.QWidget(self.centralwidget)
        self.layoutWidget2.setGeometry(QtCore.QRect(170, 10, 541, 491))
        self.layoutWidget2.setObjectName("layoutWidget2")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.layoutWidget2)
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.lbl_status = QtWidgets.QLabel(self.layoutWidget2)
        font = QtGui.QFont()
        font.setFamily("Anonymous Pro")
        font.setPointSize(8)
        self.lbl_status.setFont(font)
        self.lbl_status.setText("")
        self.lbl_status.setObjectName("lbl_status")
        self.verticalLayout_3.addWidget(self.lbl_status)
        self.text_console = QtWidgets.QPlainTextEdit(self.layoutWidget2)
        font = QtGui.QFont()
        font.setFamily("Anonymous Pro")
        font.setPointSize(8)
        self.text_console.setFont(font)
        self.text_console.setMidLineWidth(0)
        self.text_console.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.text_console.setReadOnly(True)
        self.text_console.setObjectName("text_console")
        self.verticalLayout_3.addWidget(self.text_console)
        self.lbl_stream = QtWidgets.QLabel(self.layoutWidget2)
        font = QtGui.QFont()
        font.setFamily("Anonymous Pro")
        font.setPointSize(8)
        self.lbl_stream.setFont(font)
        self.lbl_stream.setText("")
        self.lbl_stream.setObjectName("lbl_stream")
        self.verticalLayout_3.addWidget(self.lbl_stream)
        self.gb_arimu_dockstn = QtWidgets.QGroupBox(self.centralwidget)
        self.gb_arimu_dockstn.setGeometry(QtCore.QRect(10, 330, 151, 171))
        self.gb_arimu_dockstn.setCheckable(True)
        self.gb_arimu_dockstn.setChecked(False)
        self.gb_arimu_dockstn.setObjectName("gb_arimu_dockstn")
        self.layoutWidget3 = QtWidgets.QWidget(self.gb_arimu_dockstn)
        self.layoutWidget3.setGeometry(QtCore.QRect(10, 20, 131, 141))
        self.layoutWidget3.setObjectName("layoutWidget3")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.layoutWidget3)
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.btn_set_time = QtWidgets.QPushButton(self.layoutWidget3)
        self.btn_set_time.setObjectName("btn_set_time")
        self.verticalLayout_4.addWidget(self.btn_set_time)
        self.btn_set_subjname = QtWidgets.QPushButton(self.layoutWidget3)
        self.btn_set_subjname.setObjectName("btn_set_subjname")
        self.verticalLayout_4.addWidget(self.btn_set_subjname)
        self.btn_get_files = QtWidgets.QPushButton(self.layoutWidget3)
        self.btn_get_files.setObjectName("btn_get_files")
        self.verticalLayout_4.addWidget(self.btn_get_files)
        self.btn_get_file_data = QtWidgets.QPushButton(self.layoutWidget3)
        self.btn_get_file_data.setObjectName("btn_get_file_data")
        self.verticalLayout_4.addWidget(self.btn_get_file_data)
        self.btn_delete_file = QtWidgets.QPushButton(self.layoutWidget3)
        self.btn_delete_file.setObjectName("btn_delete_file")
        self.verticalLayout_4.addWidget(self.btn_delete_file)
        ARIMUViewer.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(ARIMUViewer)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 721, 21))
        self.menubar.setObjectName("menubar")
        ARIMUViewer.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(ARIMUViewer)
        self.statusbar.setObjectName("statusbar")
        ARIMUViewer.setStatusBar(self.statusbar)

        self.retranslateUi(ARIMUViewer)
        QtCore.QMetaObject.connectSlotsByName(ARIMUViewer)

    def retranslateUi(self, ARIMUViewer):
        _translate = QtCore.QCoreApplication.translate
        ARIMUViewer.setWindowTitle(_translate("ARIMUViewer", "ARIMU Viewer"))
        self.gb_arimu_commands.setTitle(_translate("ARIMUViewer", "ARIMU General Commands"))
        self.btn_ping.setText(_translate("ARIMUViewer", "Ping"))
        self.btn_get_current_filename.setText(_translate("ARIMUViewer", "Get Current  File Name"))
        self.btn_get_time.setText(_translate("ARIMUViewer", "Get Time"))
        self.btn_get_subjname.setText(_translate("ARIMUViewer", "Get Subject Name"))
        self.btn_start_stop_normal.setText(_translate("ARIMUViewer", "Start Normal"))
        self.btn_start_stop_expt.setText(_translate("ARIMUViewer", "Start Experiment"))
        self.btn_start_stop_stream.setText(_translate("ARIMUViewer", "Start Streaming"))
        self.label.setText(_translate("ARIMUViewer", "List of ARIMUs:"))
        self.btn_connect_com.setText(_translate("ARIMUViewer", "Connect"))
        self.gb_arimu_dockstn.setTitle(_translate("ARIMUViewer", "Docking Station Mode"))
        self.btn_set_time.setText(_translate("ARIMUViewer", "Set Current Time"))
        self.btn_set_subjname.setText(_translate("ARIMUViewer", "Set Subject Name"))
        self.btn_get_files.setText(_translate("ARIMUViewer", "Get List of Files"))
        self.btn_get_file_data.setText(_translate("ARIMUViewer", "Get File Data"))
        self.btn_delete_file.setText(_translate("ARIMUViewer", "Delete File"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    ARIMUViewer = QtWidgets.QMainWindow()
    ui = Ui_ARIMUViewer()
    ui.setupUi(ARIMUViewer)
    ARIMUViewer.show()
    sys.exit(app.exec_())
