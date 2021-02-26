#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 23 18:36:59 2020

@author: josef
"""
from PyQt5 import QtWidgets, uic
import PyQt5.QtCore
import numpy as np
import threading


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
        self.outgoing_packet_counter = 0
        self.uart_poll_interval = 1
        self.uart_timeout_timer = None
        self.waiting_for_response = 0
        self.serial_con = None
        
        self.threadpool = PyQt5.QtCore.QThreadPool() 
        self.poller = None
        self.RefreshComPortList()
        self.SetUartStatusIndicator("disconnected")
        
    def __bindGuiElements (self):
        self.buttonUartRefresh.clicked.connect(self.ButtonRefreshUartClicked)
        self.buttonUartConnect.clicked.connect(self.ButtonUartConnectClicked)
        self.buttonTest.clicked.connect(self.ButtonTestClicked)
        
    def ButtonTestClicked (self): 
        print("Test clicked!")
        self.UartSendCommand("status", bytearray(b'\x12\x34'))

        
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
                self.SetUartStatusIndicator("pending")
        else:
            self.isconnected = False
            uart_comm.ClosePort(self.serial_con)
            self.StopUartPollingThread()
            self.serial_con=None
            self.buttonUartConnect.setText("Connect")
            self.SetUartStatusIndicator("disconnected")
     
    def UartReceivedData(self, data):
        if self.waiting_for_response == 1:
            self.uart_timeout_timer.cancel()
            self.waiting_for_response = 0
            self.SetUartStatusIndicator("connected")
        print("Received: ")
       # print(data)
        
       
    def UartSendCommand(self, command, data): 
        tempdata = bytearray(b'\xCA\xFE') # UID
        length = len(data) + 8
        
        if command == "status": 
            cmdbyte = b'\x00'
        else:
            cmdbyte = b'\xFF' # invalid
        tempdata.extend(length.to_bytes(2, "big"))
        tempdata.extend(self.outgoing_packet_counter.to_bytes(1, "big"))
        tempdata.extend(cmdbyte)
        tempdata.extend(data)
        crcval = uart_comm.crc16(tempdata, len(tempdata))
        tempdata.extend(crcval.to_bytes(length=2, byteorder='big'))
        self.StartUartTimeout()
        self.serial_con.write(tempdata)
        print("CRC: " + hex(crcval) + " length: " + str(len(data))) 
        
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
        
    def UartTimeoutExpire(self): 
        print("Expected response form SPV not received!")
        self.SetUartStatusIndicator("pending")
        
    def StartUartTimeout(self): 
        self.waiting_for_response = 1
        self.uart_timeout_timer = threading.Timer(0.2, self.UartTimeoutExpire)
        self.uart_timeout_timer.start()
        
    def SetUartStatusIndicator(self, status): 
        if status=="disconnected": 
            self.UartStatusIndicator.setStyleSheet("background-color: red")
            self.UartStatusIndicator.setText("Disconnected")
        elif status=="pending": 
            self.UartStatusIndicator.setStyleSheet("background-color: yellow")
            self.UartStatusIndicator.setText("Pending")
        elif status =="connected": 
            self.UartStatusIndicator.setStyleSheet("background-color: green")
            self.UartStatusIndicator.setText("Connected")
        else:
            print("unexpected UART status")

app = QtWidgets.QApplication(sys.argv)
window = Ui()
app.exec_()

