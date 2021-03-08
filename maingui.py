# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'spvplayer.ui'
#
# Created by: PyQt5 UI code generator 5.10
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(932, 680)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.groupBox = QtWidgets.QGroupBox(self.centralwidget)
        self.groupBox.setGeometry(QtCore.QRect(20, 20, 471, 81))
        self.groupBox.setObjectName("groupBox")
        self.buttonUartRefresh = QtWidgets.QPushButton(self.groupBox)
        self.buttonUartRefresh.setGeometry(QtCore.QRect(10, 40, 89, 25))
        self.buttonUartRefresh.setObjectName("buttonUartRefresh")
        self.comboBoxUart = QtWidgets.QComboBox(self.groupBox)
        self.comboBoxUart.setGeometry(QtCore.QRect(110, 40, 131, 25))
        self.comboBoxUart.setObjectName("comboBoxUart")
        self.buttonUartConnect = QtWidgets.QPushButton(self.groupBox)
        self.buttonUartConnect.setGeometry(QtCore.QRect(250, 40, 89, 25))
        self.buttonUartConnect.setObjectName("buttonUartConnect")
        self.UartStatusIndicator = QtWidgets.QLabel(self.groupBox)
        self.UartStatusIndicator.setGeometry(QtCore.QRect(350, 40, 101, 17))
        self.UartStatusIndicator.setObjectName("UartStatusIndicator")
        self.buttonTest = QtWidgets.QPushButton(self.centralwidget)
        self.buttonTest.setGeometry(QtCore.QRect(20, 200, 89, 25))
        self.buttonTest.setObjectName("buttonTest")
        self.buttonGetStatus = QtWidgets.QPushButton(self.centralwidget)
        self.buttonGetStatus.setGeometry(QtCore.QRect(20, 120, 161, 25))
        self.buttonGetStatus.setObjectName("buttonGetStatus")
        self.buttonRequestChannelFill = QtWidgets.QPushButton(self.centralwidget)
        self.buttonRequestChannelFill.setGeometry(QtCore.QRect(20, 160, 161, 25))
        self.buttonRequestChannelFill.setObjectName("buttonRequestChannelFill")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 932, 22))
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        self.menuHelp = QtWidgets.QMenu(self.menubar)
        self.menuHelp.setObjectName("menuHelp")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionOpen = QtWidgets.QAction(MainWindow)
        self.actionOpen.setObjectName("actionOpen")
        self.actionAbout = QtWidgets.QAction(MainWindow)
        self.actionAbout.setObjectName("actionAbout")
        self.menuFile.addAction(self.actionOpen)
        self.menuHelp.addAction(self.actionAbout)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "SPV Player"))
        self.groupBox.setTitle(_translate("MainWindow", "Serial connection"))
        self.buttonUartRefresh.setText(_translate("MainWindow", "Refresh"))
        self.buttonUartConnect.setText(_translate("MainWindow", "Connect"))
        self.UartStatusIndicator.setText(_translate("MainWindow", "Disconnected"))
        self.buttonTest.setText(_translate("MainWindow", "Test"))
        self.buttonGetStatus.setText(_translate("MainWindow", "Get Status"))
        self.buttonRequestChannelFill.setText(_translate("MainWindow", "Request Channel Fill"))
        self.menuFile.setTitle(_translate("MainWindow", "File"))
        self.menuHelp.setTitle(_translate("MainWindow", "Help"))
        self.actionOpen.setText(_translate("MainWindow", "Open m-code"))
        self.actionAbout.setText(_translate("MainWindow", "About"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())

