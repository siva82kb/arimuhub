# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui\arimu_dreader.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_ArimuDataReader(object):
    def setupUi(self, ArimuDataReader):
        ArimuDataReader.setObjectName("ArimuDataReader")
        ArimuDataReader.resize(792, 432)
        ArimuDataReader.setMaximumSize(QtCore.QSize(792, 598))
        font = QtGui.QFont()
        font.setFamily("Bahnschrift Light")
        font.setPointSize(11)
        ArimuDataReader.setFont(font)
        self.centralwidget = QtWidgets.QWidget(ArimuDataReader)
        self.centralwidget.setObjectName("centralwidget")
        self.lbl_title = QtWidgets.QLabel(self.centralwidget)
        self.lbl_title.setGeometry(QtCore.QRect(0, 0, 281, 51))
        self.lbl_title.setStyleSheet("font: 25 20pt \"Bahnschrift Light\" ;\n"
"color: rgb(170, 0, 0);\n"
"\n"
"")
        self.lbl_title.setAlignment(QtCore.Qt.AlignJustify|QtCore.Qt.AlignVCenter)
        self.lbl_title.setObjectName("lbl_title")
        self.lbl_datetime = QtWidgets.QLabel(self.centralwidget)
        self.lbl_datetime.setGeometry(QtCore.QRect(360, 9, 421, 31))
        font = QtGui.QFont()
        font.setFamily("Anonymous Pro")
        font.setPointSize(12)
        self.lbl_datetime.setFont(font)
        self.lbl_datetime.setText("")
        self.lbl_datetime.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.lbl_datetime.setObjectName("lbl_datetime")
        self.lbl_console = QtWidgets.QLabel(self.centralwidget)
        self.lbl_console.setGeometry(QtCore.QRect(190, 50, 591, 351))
        font = QtGui.QFont()
        font.setFamily("Anonymous Pro")
        font.setPointSize(10)
        self.lbl_console.setFont(font)
        self.lbl_console.setStyleSheet("color: rgb(255, 255, 255);\n"
"background-color: rgb(0, 0, 0);")
        self.lbl_console.setFrameShape(QtWidgets.QFrame.Box)
        self.lbl_console.setText("")
        self.lbl_console.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.lbl_console.setObjectName("lbl_console")
        self.layoutWidget = QtWidgets.QWidget(self.centralwidget)
        self.layoutWidget.setGeometry(QtCore.QRect(10, 50, 171, 371))
        self.layoutWidget.setObjectName("layoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.btn_refresh_comports = QtWidgets.QPushButton(self.layoutWidget)
        self.btn_refresh_comports.setObjectName("btn_refresh_comports")
        self.verticalLayout.addWidget(self.btn_refresh_comports)
        self.list_comports = QtWidgets.QListWidget(self.layoutWidget)
        self.list_comports.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        self.list_comports.setObjectName("list_comports")
        self.verticalLayout.addWidget(self.list_comports)
        self.btn_start_data_reading = QtWidgets.QPushButton(self.layoutWidget)
        self.btn_start_data_reading.setObjectName("btn_start_data_reading")
        self.verticalLayout.addWidget(self.btn_start_data_reading)
        self.lbl_status = QtWidgets.QLabel(self.centralwidget)
        self.lbl_status.setGeometry(QtCore.QRect(190, 402, 591, 20))
        font = QtGui.QFont()
        font.setPointSize(9)
        self.lbl_status.setFont(font)
        self.lbl_status.setText("")
        self.lbl_status.setObjectName("lbl_status")
        ArimuDataReader.setCentralWidget(self.centralwidget)

        self.retranslateUi(ArimuDataReader)
        QtCore.QMetaObject.connectSlotsByName(ArimuDataReader)

    def retranslateUi(self, ArimuDataReader):
        _translate = QtCore.QCoreApplication.translate
        ArimuDataReader.setWindowTitle(_translate("ArimuDataReader", "Arimu Data Reader"))
        self.lbl_title.setText(_translate("ArimuDataReader", "  Arimu Data Reader"))
        self.btn_refresh_comports.setText(_translate("ArimuDataReader", "Refresh COM Ports"))
        self.btn_start_data_reading.setText(_translate("ArimuDataReader", "Start Reading"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    ArimuDataReader = QtWidgets.QMainWindow()
    ui = Ui_ArimuDataReader()
    ui.setupUi(ArimuDataReader)
    ArimuDataReader.show()
    sys.exit(app.exec_())

