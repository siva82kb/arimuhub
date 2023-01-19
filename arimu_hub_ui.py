# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/arimu_hub.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_ArimuHub(object):
    def setupUi(self, ArimuHub):
        ArimuHub.setObjectName("ArimuHub")
        ArimuHub.setEnabled(True)
        ArimuHub.resize(223, 203)
        ArimuHub.setMinimumSize(QtCore.QSize(223, 203))
        ArimuHub.setMaximumSize(QtCore.QSize(223, 203))
        font = QtGui.QFont()
        font.setFamily("Bahnschrift Light")
        font.setPointSize(12)
        ArimuHub.setFont(font)
        ArimuHub.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        ArimuHub.setStatusTip("")
        ArimuHub.setTabShape(QtWidgets.QTabWidget.Rounded)
        ArimuHub.setUnifiedTitleAndToolBarOnMac(False)
        self.centralwidget = QtWidgets.QWidget(ArimuHub)
        self.centralwidget.setObjectName("centralwidget")
        self.layoutWidget = QtWidgets.QWidget(self.centralwidget)
        self.layoutWidget.setGeometry(QtCore.QRect(10, 50, 201, 141))
        self.layoutWidget.setObjectName("layoutWidget")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.layoutWidget)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.btn_dev_manager = QtWidgets.QPushButton(self.layoutWidget)
        self.btn_dev_manager.setObjectName("btn_dev_manager")
        self.verticalLayout_2.addWidget(self.btn_dev_manager)
        self.btn_data_reader = QtWidgets.QPushButton(self.layoutWidget)
        self.btn_data_reader.setObjectName("btn_data_reader")
        self.verticalLayout_2.addWidget(self.btn_data_reader)
        self.btn_streaming = QtWidgets.QPushButton(self.layoutWidget)
        self.btn_streaming.setObjectName("btn_streaming")
        self.verticalLayout_2.addWidget(self.btn_streaming)
        self.btn_about = QtWidgets.QPushButton(self.layoutWidget)
        self.btn_about.setObjectName("btn_about")
        self.verticalLayout_2.addWidget(self.btn_about)
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setGeometry(QtCore.QRect(-240, 620, 47, 13))
        self.label.setObjectName("label")
        self.lbl_title = QtWidgets.QLabel(self.centralwidget)
        self.lbl_title.setGeometry(QtCore.QRect(10, 10, 201, 30))
        self.lbl_title.setStyleSheet("font: 25 20pt \"Bahnschrift Light\";\n"
"color: rgb(170, 0, 0);\n"
"")
        self.lbl_title.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_title.setObjectName("lbl_title")
        ArimuHub.setCentralWidget(self.centralwidget)

        self.retranslateUi(ArimuHub)
        QtCore.QMetaObject.connectSlotsByName(ArimuHub)

    def retranslateUi(self, ArimuHub):
        _translate = QtCore.QCoreApplication.translate
        ArimuHub.setWindowTitle(_translate("ArimuHub", "Arimu Hub"))
        self.btn_dev_manager.setText(_translate("ArimuHub", "Device Manager"))
        self.btn_data_reader.setText(_translate("ArimuHub", "Data Reader"))
        self.btn_streaming.setText(_translate("ArimuHub", "Stream Viewer"))
        self.btn_about.setText(_translate("ArimuHub", "About"))
        self.label.setText(_translate("ArimuHub", "TextLabel"))
        self.lbl_title.setText(_translate("ArimuHub", "Arimu Hub"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    ArimuHub = QtWidgets.QMainWindow()
    ui = Ui_ArimuHub()
    ui.setupUi(ArimuHub)
    ArimuHub.show()
    sys.exit(app.exec_())

