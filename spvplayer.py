#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 23 18:36:59 2020

@author: josef
"""
from PyQt5 import QtWidgets, uic
import PyQt5.QtCore
import numpy as np


import sys

import uart_comm




class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi('spvplayer.ui', self)
        
        self.__initialize()
        self.__bindGuiElements()
        self.show()  
    
    def __initialize (self):
        self.isconnected = False
        self.baudrate = 115200
        self.uart_timeout = 10
        self.uart_poll_interval = 1
        self.serial_con = None
        self.threadpool = PyQt5.QtCore.QThreadPool() 
        self.poller = None
        self.RefreshComPortList()
        
    def __bindGuiElements (self):
        self.buttonUartRefresh.clicked.connect(self.ButtonRefreshUartClicked)
        self.buttonUartConnect.clicked.connect(self.ButtonUartConnectClicked)
        self.buttonTest.clicked.connect(self.ButtonTestClicked)
        
    def ButtonTestClicked (self): 
        print("Test clicked!")
        self.serial_con.write(b'\xCA\xFE\x00\x08\x00\x01\xFF\xFF')
        
    def ButtonRefreshUartClicked (self):
        print("Refresh")       
        self.RefreshComPortList()
    
    def ButtonUartConnectClicked (self):
        if self.isconnected == False:
            com_sel = self.comboBoxUart.currentText()
            self.serial_con = uart_comm.OpenPort(com_sel, self.baudrate)
            if (not(self.serial_con == None)):
                self.isconnected = True
                self.StartUartPollingThread(self.serial_con)
                self.buttonUartConnect.setText("Disconnect")
                print("Connection to " + str(com_sel) + " successful!")
        else:
            self.isconnected = False
            uart_comm.ClosePort(self.serial_con)
            self.StopUartPollingThread()
            self.serial_con=None
            self.buttonUartConnect.setText("Connect")
     
    def UartReceivedData(self, data):
        print(data)
        
    def RefreshComPortList(self):
        ports_list = uart_comm.GetPorts()
        print(ports_list)
        self.comboBoxUart.clear()
        self.comboBoxUart.addItems(ports_list)
    
    def StartUartPollingThread (self, serial_con): 
        self.poller = uart_comm.UartReceiveThread(serial_con)
        self.poller.signals.received_data.connect(self.UartReceivedData)
        self.threadpool.start(self.poller)
        
    def StopUartPollingThread (self):
        if not self.poller == None:
            self.poller.exit()
        self.poller = None

app = QtWidgets.QApplication(sys.argv)
window = Ui()
app.exec_()

