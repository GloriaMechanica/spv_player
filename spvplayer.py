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
import channels

testpositions_xy = [500, 	500, 	1550, 	250, 	2000, 	0, 		100, 		0]
testtimes_xy = 	  [300, 	400, 	500, 	600, 	500, 	500, 	100, 	100]
testpositions_z = [1000, 	2000, 	3100, 	500, 	10000, 	0, 		400, 	0,  500]
testtimes_z = 	  [300, 	400, 	500, 	600, 	1000, 	1000, 	200, 	500, 500]

class UartPacketErrors:
    packetCorrect = 0
    packetTooShort = 1
    packetTooLong = 2
    packetUIDError = 3
    packetCRCError = 4
    packetNACK = 5

# in brackets [x,y]: x...number of tag, y...length of data field in tag
SPVAnswerTags = { 
    "SoftwareVersion" : [0, 2],
    "CurrentSystemTime" : [1, 4],
    "TimeRunning" : [2, 1],
    "DatapointsMissing" : [3, 2],
    "ChannelReady" : [4, 1]
    }

SPVChannelNumbers = {
    "G_NOTE" : 0,
    "D_NOTE" : 1,
    "A_NOTE" : 2,
    "E_NOTE" : 3,
    "POSX_DAE" : 4,
    "POSY_DAE" : 5,
    "STR_DAE" : 6,
    "POSX_GDA" : 7,
    "POSY_GDA" : 8,
    "STR_GDA" : 9,
    "G_VIB" : 10,
    "D_VIB" : 11,
    "A_VIB" : 12,
    "E_VIB" : 13
}
SPVAnswerTagsLookup = dict(zip(list(np.array(list(SPVAnswerTags.values()))[:,0]), SPVAnswerTags.keys()))

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

        # Channel buffer structures
        self.cha_posx_dae = channels.ChannelStructure()
        self.cha_posy_dae = channels.ChannelStructure()
        self.cha_str_dae = channels.ChannelStructure()
        self.AddTestDataToBuffers()

        self.isconnected = False
        self.outgoing_packet_counter = 0
        self.uart_timeout_timer = None
        self.waiting_for_response = 0
        self.serial_con = None
        self.resend_counter = 0
        self.last_command = None # used to keep the command in case it needs to be resent
        self.last_data = None # used to keep the data in case it needs to be resent
        
        self.threadpool = PyQt5.QtCore.QThreadPool() 
        self.poller = None
        self.RefreshComPortList()
        self.SetUartStatusIndicator("disconnected")
        
    def __bindGuiElements (self):
        self.buttonUartRefresh.clicked.connect(self.ButtonRefreshUartClicked)
        self.buttonUartConnect.clicked.connect(self.ButtonUartConnectClicked)
        self.buttonTest.clicked.connect(self.ButtonTestClicked)
        self.buttonRequestChannelFill.clicked.connect(self.ButtonRequestChannelFillClicked)
        self.buttonGetStatus.clicked.connect(self.ButtonGetStatusClicked)
        
    def ButtonTestClicked (self): 
        print("Test clicked!")
        print(self.cha_str_dae.getNextDatapoints(2))
        print("Advanced time to " + str(self.cha_str_dae.getTimeOfLastExecutedDatapoint()) + "ms")

    def AddTestDataToBuffers(self):
        block = []
        for idx, time in enumerate(testtimes_xy):
            block.append({"timediff": time, "pos": testpositions_xy[idx]})
        self.cha_posx_dae.appendDatapoints(block)
        self.cha_posy_dae.appendDatapoints(block)

        block = []
        for idx, time in enumerate(testtimes_z):
            block.append({"timediff": time, "pos": testpositions_z[idx]})
        self.cha_str_dae.appendDatapoints(block)
        print("Added test data to channels")

    def ButtonGetStatusClicked(self):
        self.UartSendCommand("getStatus", None)

    def ButtonRequestChannelFillClicked(self):
        print("Requesting channel fill")
        self.UartSendCommand("requestChannelFill", None)
        
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
        check = self.UartCheckPacket(data)
        if self.waiting_for_response == 1 and check == UartPacketErrors.packetCorrect: 
            self.uart_timeout_timer.cancel()
            self.waiting_for_response = 0
            self.SetUartStatusIndicator("connected")
        print("Check result: "+ str(check))
        self.DecodePacket(data)
        
    def DecodePacket(self, data): 
        # The packet is ok, so we can decode its contents.
        data_length =  int.from_bytes(data[2:4], 'big') - self.settings.minimal_packet_length
        print("Databytes unpacket: " + str(data_length))
        
        result = self.SplitDecodeTLV(data[6:(data_length+6)])
        print(result)

    # This function returns a byte array that can be packed as data to the sendDatapoints command
    # it takes a list of tags, finds those that are "DatapointsMissing" and prepares the according data points
    def PrepareChannelDatapoints(self, list_of_missing_points):
        data = bytearray()
        for tag in list_of_missing_points:
            if tag[0] == 'DatapointsMissing':
                data.extend(tag[1])
                if tag[1] == SPVChannelNumbers["POSX_DAE"] or tag[1] == SPVChannelNumbers["POSY_DAE"]:
                    print("Bla1")
                elif tag[1] == SPVChannelNumbers["STR_DAE"]:
                    print("Bla2")


    def SplitDecodeTLV(self, data): 
        total_length = len(data)
        result = []
        ptr = 0
        while (ptr < total_length):
            cmd = data[ptr]
            command_string = SPVAnswerTagsLookup[cmd]
            length = data[ptr+1]
            datum = data[ptr+2:ptr+2+length]
            if (command_string == "SoftwareVersion" and length==SPVAnswerTags[command_string][1]):
                id1 = datum[0]
                id2 = datum[1]
                result.append([command_string, id1, id2])
            elif (command_string == "CurrentSystemTime" and length==SPVAnswerTags[command_string][1]):
                systime = int.from_bytes(datum, 'little')
                result.append([command_string, systime])
            elif (command_string == "TimeRunning" and length==SPVAnswerTags[command_string][1]):
                running = datum[0]
                result.append([command_string, running])
            elif (command_string == "DatapointsMissing" and length==SPVAnswerTags[command_string][1]):
                channel_nr = datum[0]
                missing = datum[1]
                result.append([command_string, channel_nr, missing])
            ptr = ptr + length + 2
        return result
       
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
        self.resend_counter = 0
        self.UartTransmitCommand(command, data)
        self.StartUartTimeout()
        
    def UartResendCommand(self): 
        self.UartTransmitCommand(self.last_command, self.last_data)
        self.StartUartTimeout()

        
    def UartTransmitCommand(self, command, data): 
        tempdata = bytearray(b'\xCA\xFE') # UID
        if data != None:
            length = len(data) + 8
        else:
            length = 8
        
        if command == "getStatus":
            cmdbyte = b'\x00'
        elif command == "requestChannelFill":
            cmdbyte = b'\x02'
        elif command == "sendDatapoints":
            cmdbyte = b'\x03'
        else:
            cmdbyte = b'\xFF' # invalid
        tempdata.extend(length.to_bytes(2, "big"))
        tempdata.extend(self.outgoing_packet_counter.to_bytes(1, "big"))
        tempdata.extend(cmdbyte)
        if data != None:
            tempdata.extend(data)
        crcval = uart_comm.crc16(tempdata, len(tempdata))
        tempdata.extend(crcval.to_bytes(length=2, byteorder='big'))
        self.serial_con.write(tempdata)
        self.last_command = command # store in case it needs to be resent
        self.last_data = data
        print("Send: CRC=" + hex(crcval) + " length=" + str(length))
        
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
        if self.resend_counter < self.settings.resend_tries: 
            self.resend_counter = self.resend_counter + 1
            self.UartResendCommand()
            print("Resending command.")
        else:
            print("Exceeded resend tries!")
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

