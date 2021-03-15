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
import settings
import mcode

class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi('spvplayer.ui', self)
        
        self.__initialize()
        self.__bindGuiElements()
        self.show()  
    
    def __initialize (self):
        # Settings
        self.settings = settings.Settings()
        print(self.settings.packet_UID)

        self.spvcomm = uart_comm.SPVUartConnection({"receive_handler":self.UartReceiveEvent,
                                                    "error_handler":self.UartErrorOccured})

        # Channel buffer structures
        self.cha_posx_dae = channels.ChannelStructure(settings.SPVChannelNumbers["POSX_DAE"])
        self.cha_posy_dae = channels.ChannelStructure(settings.SPVChannelNumbers["POSY_DAE"])
        self.cha_str_dae = channels.ChannelStructure(settings.SPVChannelNumbers["STR_DAE"])
        self.AddTestDataToBuffers()

        calibration = []
        self.mcreader = mcode.McodeReader(calibration)

        self.RefreshComPortList()
        self.SetUartStatusIndicator("disconnected")
        
    def __bindGuiElements (self):
        self.buttonUartRefresh.clicked.connect(self.ButtonRefreshUartClicked)
        self.buttonUartConnect.clicked.connect(self.ButtonUartConnectClicked)
        self.buttonTest.clicked.connect(self.ButtonTestClicked)
        self.buttonRequestChannelFill.clicked.connect(self.ButtonRequestChannelFillClicked)
        self.buttonGetStatus.clicked.connect(self.ButtonGetStatusClicked)
        self.buttonRewind.clicked.connect(self.ButtonRewindClicked)
        self.buttonInitSPV.clicked.connect(self.ButtonInitSPVClicked)
        self.buttonStartPlaying.clicked.connect(self.ButtonStartPlayingClicked)
        self.buttonStopPlaying.clicked.connect(self.ButtonStopPlayingClicked)
        self.buttonClearChannels.clicked.connect(self.ButtonClearChannelsClicked)

    def ButtonTestClicked (self): 
        print("Test clicked!")
        self.mcreader.parseFile("test.mc")

    def ButtonGetStatusClicked(self):
        self.spvcomm.UartSendCommand("getStatus", None)

    def ButtonRequestChannelFillClicked(self):
        print("Requesting channel fill")
        self.spvcomm.UartSendCommand("requestChannelFill", None)
        
    def ButtonRefreshUartClicked (self):
        print("Refresh")       
        self.RefreshComPortList()
    
    def ButtonUartConnectClicked (self):
        if self.spvcomm.getConnectState() == False:
            com_sel = self.comboBoxUart.currentText()
            ret = self.spvcomm.connectCOMPort(com_sel)
            if ret is not None:
                self.buttonUartConnect.setText("Disconnect")
                print("Connection to " + str(com_sel) + " successful!")
                self.SetUartStatusIndicator("pending")
        else:
            self.spvcomm.disconnectCOMPort()
            self.buttonUartConnect.setText("Connect")
            self.SetUartStatusIndicator("disconnected")

    def ButtonRewindClicked(self):
        self.cha_posx_dae.resetTimeToStart()
        self.cha_posy_dae.resetTimeToStart()
        self.cha_str_dae.resetTimeToStart()

    def ButtonInitSPVClicked(self):
        print("Init not implemented yet!")

    def ButtonClearChannelsClicked(self):
        self.spvcomm.UartSendCommand("clearChannels", None)
        print("Clear Channels")

    def ButtonStartPlayingClicked(self):
        self.spvcomm.UartSendCommand("startPlaying", None)
        print("Start Playing")


    def ButtonStopPlayingClicked(self):
        self.spvcomm.UartSendCommand("stopPlaying", None)
        print("Stop Playing")

    def UartReceiveEvent(self, data):
        print("Something has been received")
        self.SetUartStatusIndicator("connected")
        tags = self.spvcomm.DecodePacket(data)
        print(tags)

        self.HandDatapointsToSPV(tags)


    def HandDatapointsToSPV(self, tags):
        # If any requests for new datapoints are among the tags, we prepare the data now.
        data = bytearray()
        budget = self.settings.maximum_datapoints_per_transfer
        for tag in tags:
            if tag["tag"] == 'DatapointsMissing':
                channel = None
                if tag["channel"] == settings.SPVChannelNumbers["POSX_DAE"]:
                    channel = self.cha_posx_dae
                elif tag["channel"] == settings.SPVChannelNumbers["POSY_DAE"]:
                    channel = self.cha_posy_dae
                elif tag["channel"] == settings.SPVChannelNumbers["STR_DAE"]:
                    channel = self.cha_str_dae
                if channel is not None:
                    requested_datapoints = min(budget, tag["missing"])
                    [number, block] = self.spvcomm.PrepareChannelDatapoints(channel, requested_datapoints)
                    budget = budget - number
                    data.extend(block)
        if len(data) > 0:
            self.spvcomm.UartSendCommand("sendDatapoints", data)

    def UartErrorOccured(self, type):
        self.SetUartStatusIndicator("pending")
        print(type)

    def RefreshComPortList(self):
        ports_list = uart_comm.GetPorts()
        print(ports_list)
        self.comboBoxUart.clear()
        self.comboBoxUart.addItems(ports_list)
        
    def SetUartStatusIndicator(self, status): 
        if status == "disconnected":
            self.UartStatusIndicator.setStyleSheet("background-color: red")
            self.UartStatusIndicator.setText("Disconnected")
        elif status == "pending":
            self.UartStatusIndicator.setStyleSheet("background-color: yellow")
            self.UartStatusIndicator.setText("Pending")
        elif status == "connected":
            self.UartStatusIndicator.setStyleSheet("background-color: green")
            self.UartStatusIndicator.setText("Connected")
        else:
            print("unexpected UART status")

    def AddTestDataToBuffers(self):
        block = []
        for idx, time in enumerate(settings.testtimes_xy):
            block.append({"timediff": time, "pos": settings.testpositions_xy[idx]})
        self.cha_posx_dae.appendDatapoints(block)
        self.cha_posy_dae.appendDatapoints(block)

        block = []
        for idx, time in enumerate(settings.testtimes_z):
            block.append({"timediff": time, "pos": settings.testpositions_z[idx]})
        self.cha_str_dae.appendDatapoints(block)
        print("Added test data to channels")

app = QtWidgets.QApplication(sys.argv)
window = Ui()
app.exec_()

