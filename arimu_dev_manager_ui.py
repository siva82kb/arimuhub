# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/arimu_dev_manager.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_ArimuDevManager(object):
    def setupUi(self, ArimuDevManager):
        ArimuDevManager.setObjectName("ArimuDevManager")
        ArimuDevManager.resize(815, 435)
        font = QtGui.QFont()
        font.setFamily("Bahnschrift Light")
        font.setPointSize(10)
        ArimuDevManager.setFont(font)
        ArimuDevManager.setStatusTip("")
        self.centralwidget = QtWidgets.QWidget(ArimuDevManager)
        self.centralwidget.setObjectName("centralwidget")
        self.layoutWidget = QtWidgets.QWidget(self.centralwidget)
        self.layoutWidget.setGeometry(QtCore.QRect(10, 40, 281, 214))
        self.layoutWidget.setObjectName("layoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.btn_refresh_com = QtWidgets.QPushButton(self.layoutWidget)
        self.btn_refresh_com.setObjectName("btn_refresh_com")
        self.verticalLayout.addWidget(self.btn_refresh_com)
        self.list_com_ports = QtWidgets.QListWidget(self.layoutWidget)
        self.list_com_ports.setObjectName("list_com_ports")
        self.verticalLayout.addWidget(self.list_com_ports)
        self.btn_connect_com = QtWidgets.QPushButton(self.layoutWidget)
        self.btn_connect_com.setObjectName("btn_connect_com")
        self.verticalLayout.addWidget(self.btn_connect_com)
        self.layoutWidget1 = QtWidgets.QWidget(self.centralwidget)
        self.layoutWidget1.setGeometry(QtCore.QRect(300, 70, 511, 351))
        self.layoutWidget1.setObjectName("layoutWidget1")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.layoutWidget1)
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.text_console = QtWidgets.QPlainTextEdit(self.layoutWidget1)
        font = QtGui.QFont()
        font.setFamily("Anonymous Pro")
        font.setPointSize(8)
        self.text_console.setFont(font)
        self.text_console.setMidLineWidth(0)
        self.text_console.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.text_console.setReadOnly(True)
        self.text_console.setObjectName("text_console")
        self.verticalLayout_3.addWidget(self.text_console)
        self.lbl_status = QtWidgets.QLabel(self.layoutWidget1)
        font = QtGui.QFont()
        font.setFamily("Anonymous Pro")
        font.setPointSize(8)
        self.lbl_status.setFont(font)
        self.lbl_status.setText("")
        self.lbl_status.setObjectName("lbl_status")
        self.verticalLayout_3.addWidget(self.lbl_status)
        self.lbl_title = QtWidgets.QLabel(self.centralwidget)
        self.lbl_title.setGeometry(QtCore.QRect(10, -8, 741, 51))
        self.lbl_title.setStyleSheet("font: 25 20pt \"Bahnschrift Light\" ;\n"
"color: rgb(170, 0, 0);\n"
"\n"
"")
        self.lbl_title.setAlignment(QtCore.Qt.AlignJustify|QtCore.Qt.AlignVCenter)
        self.lbl_title.setObjectName("lbl_title")
        self.text_arimu_dev_details = QtWidgets.QPlainTextEdit(self.centralwidget)
        self.text_arimu_dev_details.setGeometry(QtCore.QRect(10, 260, 281, 161))
        font = QtGui.QFont()
        font.setFamily("Anonymous Pro")
        font.setPointSize(8)
        self.text_arimu_dev_details.setFont(font)
        self.text_arimu_dev_details.setReadOnly(True)
        self.text_arimu_dev_details.setPlainText("")
        self.text_arimu_dev_details.setObjectName("text_arimu_dev_details")
        self.widget = QtWidgets.QWidget(self.centralwidget)
        self.widget.setGeometry(QtCore.QRect(300, 40, 511, 26))
        self.widget.setObjectName("widget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.widget)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.btn_set_time = QtWidgets.QPushButton(self.widget)
        self.btn_set_time.setObjectName("btn_set_time")
        self.horizontalLayout.addWidget(self.btn_set_time)
        self.btn_set_subjname = QtWidgets.QPushButton(self.widget)
        self.btn_set_subjname.setObjectName("btn_set_subjname")
        self.horizontalLayout.addWidget(self.btn_set_subjname)
        self.btn_get_files = QtWidgets.QPushButton(self.widget)
        self.btn_get_files.setObjectName("btn_get_files")
        self.horizontalLayout.addWidget(self.btn_get_files)
        self.btn_get_file_data = QtWidgets.QPushButton(self.widget)
        self.btn_get_file_data.setObjectName("btn_get_file_data")
        self.horizontalLayout.addWidget(self.btn_get_file_data)
        ArimuDevManager.setCentralWidget(self.centralwidget)

        self.retranslateUi(ArimuDevManager)
        QtCore.QMetaObject.connectSlotsByName(ArimuDevManager)

    def retranslateUi(self, ArimuDevManager):
        _translate = QtCore.QCoreApplication.translate
        ArimuDevManager.setWindowTitle(_translate("ArimuDevManager", "Arimu Device Manager"))
        self.btn_refresh_com.setText(_translate("ArimuDevManager", "Refresh COM Ports"))
        self.btn_connect_com.setText(_translate("ArimuDevManager", "Connect"))
        self.lbl_title.setText(_translate("ArimuDevManager", "  Arimu Device Manager"))
        self.btn_set_time.setText(_translate("ArimuDevManager", "Set Current Time"))
        self.btn_set_subjname.setText(_translate("ArimuDevManager", "Set Subject Name"))
        self.btn_get_files.setText(_translate("ArimuDevManager", "Get List of Files"))
        self.btn_get_file_data.setText(_translate("ArimuDevManager", "Get File Data"))

