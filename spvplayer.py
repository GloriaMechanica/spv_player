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
import machine
import maingui

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
        self.channels = {
            "g_note" : None,
            "d_note" : None,
            "a_note" : None,
            "e_note" : channels.ChannelStructure(settings.SPVChannelNumbers["e_note"]),
            "posx_dae" : channels.ChannelStructure(settings.SPVChannelNumbers["posx_dae"]),
            "posy_dae" :channels.ChannelStructure(settings.SPVChannelNumbers["posy_dae"]),
            "str_dae" : channels.ChannelStructure(settings.SPVChannelNumbers["str_dae"]),
            "posx_gda" : None,
            "posy_gda" : None,
            "str_gda" : None,
            "g_vib" : None,
            "d_vib": None,
            "a_vib": None,
            "e_vib" : None,
        }

        #self.AddTestDataToBuffers()

        self.mcreader = mcode.McodeReader(settings.calibration)
        self.machine = machine.Machine_SPV()


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
        self.buttonReadMcode.clicked.connect(self.ButtonReadMcodeClicked)
        self.buttonMoveENoteTo.clicked.connect(self.ButtonMoveENoteClicked)
        self.buttonMovePosxTo.clicked.connect(self.ButtonMovePosxClicked)
        self.buttonMovePosyTo.clicked.connect(self.ButtonMovePosyClicked)
        self.buttonMoveStrTo.clicked.connect(self.ButtonMoveStrClicked)
        self.buttonGetMachineStatus.clicked.connect(self.ButtonGetMachineStatusClicked)
    def ButtonTestClicked (self): 
        print("Test clicked!")


    def ButtonGetStatusClicked(self):
        self.spvcomm.UartSendCommand("getStatus", None)

    def ButtonGetMachineStatusClicked(self):
        self.spvcomm.UartSendCommand("getMachineStatus", None)

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
        self.channels["posx_dae"].resetTimeToStart()
        self.channels["posy_dae"].resetTimeToStart()
        self.channels["str_dae"].resetTimeToStart()

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

    def ButtonReadMcodeClicked(self):
        data = self.mcreader.parseFile("test.mc")
        if data is None:
            print("Parse error!")
        else:
            for d in data:
                print(d)
            self.mcreader.pushMcodeDataToChannels(data, self.channels, self.machine)
        print("Status of posx_dae channel")
        buf = self.channels["posx_dae"].getChannelBuffer()
        for b in buf:
            print(b)
        buf = self.channels["posy_dae"].getChannelBuffer()
        for b in buf:
            print(b)
        buf = self.channels["str_dae"].getChannelBuffer()
        for b in buf:
            print(b)

    def ButtonMoveENoteClicked(self):
        self.spvcomm.MoveAxisTo("e_note", 0, 0)

    def ButtonMovePosxClicked(self):
        self.spvcomm.MoveAxisTo("posx_dae", int(self.textinPosxPos.text()), 20)

    def ButtonMovePosyClicked(self):
        self.spvcomm.MoveAxisTo("posy_dae", int(self.textinPosyPos.text()), 20)

    def ButtonMoveStrClicked(self):
        self.spvcomm.MoveAxisTo("str_dae",  int(self.textinStrPos.text()), 20)

    def UartReceiveEvent(self, data):
        print("Something has been received")
        self.SetUartStatusIndicator("connected")
        tags = self.spvcomm.DecodePacket(data)
        print(tags)

        self.HandDatapointsToSPV(tags)
        self.UpdateMachineStatus(tags)

    def UpdateMachineStatus(self, tags):
        for tag in tags:
            if tag["tag"] == "AxisStatus":
                if tag["channel"] == settings.SPVChannelNumbers["posx_dae"]:
                    self.lblPOSXDAEPos.setText(str(tag["position"]))
                elif tag["channel"] == settings.SPVChannelNumbers["posy_dae"]:
                    self.lblPOSYDAEPos.setText(str(tag["position"]))
                elif tag["channel"] == settings.SPVChannelNumbers["str_dae"]:
                    self.lblSTRDAEPos.setText(str(tag["position"]))

    def HandDatapointsToSPV(self, tags):
        # If any requests for new datapoints are among the tags, we prepare the data now.
        data = bytearray()
        budget = self.settings.maximum_datapoints_per_transfer
        for tag in tags:
            if tag["tag"] == 'DatapointsMissing':
                channel = None
                if tag["channel"] == settings.SPVChannelNumbers["posx_dae"]:
                    channel = self.channels["posx_dae"]
                elif tag["channel"] == settings.SPVChannelNumbers["posy_dae"]:
                    channel = self.channels["posy_dae"]
                elif tag["channel"] == settings.SPVChannelNumbers["str_dae"]:
                    channel = self.channels["str_dae"]
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
        self.channels["posx_dae"].appendDatapoints(block)
        self.channels["posy_dae"].appendDatapoints(block)

        block = []
        for idx, time in enumerate(settings.testtimes_z):
            block.append({"timediff": time, "pos": settings.testpositions_z[idx]})
        self.channels["str_dae"].appendDatapoints(block)
        print("Added test data to channels")

app = QtWidgets.QApplication(sys.argv)
window = Ui()
app.exec_()

