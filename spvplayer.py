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
import struct


import sys

import uart_comm

class UartPacketErrors:
    packetCorrect = 0
    packetTooShort = 1
    packetTooLong = 2
    packetUIDError = 3
    packetCRCError = 4
    packetNACK = 5

class Settings: 
    minimal_packet_length = 8
    baudrate = 115200
    uart_timeout = 10
    responseTimeout = 500 #ms If no response from the SPV is recieved within, its an error
    uart_poll_interval = 200 # ms: UART checked for new data in this interval 
    resend_tries = 3 # a command is retried that many times if the SPV responds with a NACK
    packet_UID = bytes(b'\xCA\xFE')
    ack = 0

class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi('spvplayer.ui', self)
        
        self.__initialize()
        self.__bindGuiElements()
        self.show()  
    
    def __initialize (self):
        # Settings
        self.settings = Settings()
        print(self.settings.packet_UID)

        self.isconnected = False
        self.outgoing_packet_counter = 0
        self.uart_timeout_timer = None
        self.waiting_for_response = 0
        self.serial_con = None
        self.resend_counter = 0
        
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
        self.UartSendCommand("status", bytearray(b'\x12\x34\x56\x78'))

        
    def ButtonRefreshUartClicked (self):
        print("Refresh")       
        self.RefreshComPortList()
    
    def ButtonUartConnectClicked (self):
        if self.isconnected == False:
            com_sel = self.comboBoxUart.currentText()
            self.serial_con = uart_comm.OpenPort(com_sel, self.settings.baudrate)
            if (not(self.serial_con == None)):
                self.isconnected = True
                self.StartUartPollingThread(self.serial_con, self.settings.uart_poll_interval)
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
        
        check = self.UartCheckPacket(data)
        print("Check result: "+ str(check))
       # print(data)
       
    def UartCheckPacket(self, data): 
        length = len(data)
        print("Check packet of length " + str(length))
        
        if length < self.settings.minimal_packet_length: 
            print("Packet smaller minimal length!")
            return UartPacketErrors.packetTooShort
        if data[0:2] != self.settings.packet_UID: 
            print("UID invalid!")
            return UartPacketErrors.packetUIDError
        
        expected_length =  int.from_bytes(data[2:4], 'big') 
        print("Expected length: " + str(expected_length))
        if expected_length < length: 
            print("Real packet length smaller than expected.")
            return UartPacketErrors.packetTooShort
        elif expected_length > length: 
            print("Real packet length bigger than expected.")
            return UartPacketErrors.packetTooLong
        # ignore packet counter for now...
        acknowledge = data[5]
        if acknowledge != self.settings.ack: 
            print("SPV sent NACK!")
            return UartPacketErrors.packetNACK
        
        crc_calc = uart_comm.crc16(data, length-2)
        crc_received = int.from_bytes(data[(length-2):(length)], 'big')
        if crc_calc != crc_received: 
            print("CRC of received package flawed!")
            return UartPacketErrors.packetCRCError
        
        return UartPacketErrors.packetCorrect
       
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
    
    def StartUartPollingThread (self, serial_con, response_timeout): 
        self.poller = uart_comm.UartReceiveThread(serial_con, response_timeout)
        self.poller.signals.received_data.connect(self.UartReceivedData)
        self.threadpool.start(self.poller)
        
    def StopUartPollingThread (self):
        if not self.poller == None:
            self.poller.exit()
        self.poller = None
        
    def UartTimeoutExpire(self): 
        print("Expected response form SPV not received!")
        self.SetUartStatusIndicator("pending")
        self.waiting_for_response = 0
        
    def StartUartTimeout(self): 
        # Timeout until the response (Ack/Nack) should arrive from the SPV 
        self.waiting_for_response = 1
        self.uart_timeout_timer = threading.Timer(self.settings.responseTimeout/1e3, self.UartTimeoutExpire)
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

