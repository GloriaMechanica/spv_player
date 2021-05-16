#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 23 18:36:59 2020

@author: josef
"""
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QFileDialog
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
    
    def __initialize(self):
        # M-Code filename
        self.m_code_file_name = ""  # We will get this via OpenFileDialog

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
        self.MCodeFileName.setStyleSheet("background-color: red")

        self.AutoMachineUpdateTimer = None
        self.AutoMachineUpdateRunning = 0
        
    def __bindGuiElements (self):
        self.actionOpen.triggered.connect(self.OpenFileDialog)
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


        self.buttonGetMachineStatus.clicked.connect(self.ButtonGetMachineStatusClicked)
        self.buttonMachineStatusUpdate.clicked.connect(self.ButtonMachineStatusUpdateClicked)
        self.buttonReferenceLimitSwitches.clicked.connect(self.ButtonReferenceAxisClicked)

        # Manual Move
        self.buttonMoveENoteTo.clicked.connect(self.ButtonMoveENoteClicked)
        self.buttonMovePosxTo.clicked.connect(self.ButtonMovePosxClicked)
        self.buttonMovePosyTo.clicked.connect(self.ButtonMovePosyClicked)
        self.buttonMoveStrTo.clicked.connect(self.ButtonMoveStrClicked)
        self.buttonPOSXDAEMoveRelPositive.clicked.connect(self.ButtonMovePosxRelPlusClicked)
        self.buttonPOSYDAEMoveRelPositive.clicked.connect(self.ButtonMovePosyRelPlusClicked)
        self.buttonSTRDAEMoveRelPositive.clicked.connect(self.ButtonMoveStrRelPlusClicked)
        self.buttonPOSXDAEMoveRelNegative.clicked.connect(self.ButtonMovePosxRelMinusClicked)
        self.buttonPOSYDAEMoveRelNegative.clicked.connect(self.ButtonMovePosyRelMinusClicked)
        self.buttonSTRDAEMoveRelNegative.clicked.connect(self.ButtonMoveStrRelMinusClicked)
        self.ButtonMovePosLevers.clicked.connect(self.ButtonMovePosLeversClicked)
        self.ButtonMoveStrAxis.clicked.connect(self.ButtonMoveStrAxisClicked)
        self.ButtonPredefinedPositionE.clicked.connect(self.ButtonPredefinedPositionEClicked)
        self.ButtonPredefinedPositionA.clicked.connect(self.ButtonPredefinedPositionAClicked)
        self.ButtonPredefinedPositionD.clicked.connect(self.ButtonPredefinedPositionDClicked)


        # Calibration
        self.buttonCalculateCal.clicked.connect(self.ButtonCalculateCalClicked)
        self.buttonCalDString.clicked.connect(self.ButtonCalDStringClicked)
        self.buttonCalAString.clicked.connect(self.ButtonCalAStringClicked)
        self.buttonCalStrMin.clicked.connect(self.ButtonCalStrMinClicked)
        self.buttonCalStrMax.clicked.connect(self.ButtonCalStrMaxClicked)

    def ButtonTestClicked (self): 
        print("test clicked")

    def OpenFileDialog(self):
        options = QFileDialog.Options()
        return_val = QFileDialog.getOpenFileName(self, "Open M-Code File", "",
                                                  "M-Code Files (*.mc);;All Files (*)", options=options)
        self.m_code_file_name = return_val[0]
        self.MCodeFileName.setText(self.m_code_file_name)
        if self.m_code_file_name:
            self.MCodeFileName.setStyleSheet("background-color: green")
        else:
            self.MCodeFileName.setStyleSheet("background-color: red")
            self.MCodeFileName.setText("No M-Code File selected")

    def ButtonMachineStatusUpdateClicked(self):
        if self.AutoMachineUpdateRunning == 0:
            self.StartAutoRefreshTimer()
            self.AutoMachineUpdateRunning = 1
            self.buttonMachineStatusUpdate.setText("Stop Update")
        else:
            self.AutoMachineUpdateRunning = 0
            self.buttonMachineStatusUpdate.setText("Start Update")

    def ButtonGetStatusClicked(self):
        self.spvcomm.SPVSendCommand("getStatus", None)

    def ButtonGetMachineStatusClicked(self):
        self.spvcomm.SPVSendCommand("getMachineStatus", None)

    def ButtonRequestChannelFillClicked(self):
        print("Requesting channel fill")
        self.spvcomm.SPVSendCommand("requestChannelFill", None)
        
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
        self.spvcomm.SPVSendCommand("clearChannels", None)
        print("Clear Channels")

    def ButtonStartPlayingClicked(self):
        self.spvcomm.SPVSendCommand("startPlaying", None)
        print("Start Playing")

    def ButtonStopPlayingClicked(self):
        self.spvcomm.SPVSendCommand("stopPlaying", None)
        print("Stop Playing")

    def ButtonReadMcodeClicked(self):

        if not self.m_code_file_name:
            print("E: No M-Code File selected, nothing to read!")
            return
        data = self.mcreader.parseFile(self.m_code_file_name)
        if data is None:
            print("E: Parse error!")
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

    def ButtonMovePosxRelPlusClicked(self):
        self.spvcomm.MoveAxisRelative("posx_dae", int(self.textinPOSXDAEMoveRel.text()), 20)

    def ButtonMovePosyRelPlusClicked(self):
        self.spvcomm.MoveAxisRelative("posy_dae", int(self.textinPOSYDAEMoveRel.text()), 20)

    def ButtonMoveStrRelPlusClicked(self):
        self.spvcomm.MoveAxisRelative("str_dae", int(self.textinSTRDAEMoveRel.text()), 20)

    def ButtonMovePosxRelMinusClicked(self):
        self.spvcomm.MoveAxisRelative("posx_dae", -int(self.textinPOSXDAEMoveRel.text()), 20)

    def ButtonMovePosyRelMinusClicked(self):
        self.spvcomm.MoveAxisRelative("posy_dae", -int(self.textinPOSYDAEMoveRel.text()), 20)

    def ButtonMoveStrRelMinusClicked(self):
        self.spvcomm.MoveAxisRelative("str_dae", -int(self.textinSTRDAEMoveRel.text()), 20)

    def ButtonReferenceAxisClicked(self):
        self.spvcomm.ReferenceAxis("posx_dae", 5)
        self.spvcomm.ReferenceAxis("posy_dae", 5)
        #For test only reference x axis

    def ButtonMovePosLeversClicked(self):
        r = float(self.textinManualMoveR.text())
        phi = float(self.textinManualMovePhi.text())
        point = {"channel":"pos_dae", "paramlist":[r, phi]}
        [steps_x, steps_y] = self.machine.convert_pos_point(point, settings.calibration)
        self.spvcomm.MoveAxisTo("posx_dae", steps_x, int(self.textinManualMovePosSpeed.text()))
        self.spvcomm.MoveAxisTo("posy_dae", steps_y, int(self.textinManualMovePosSpeed.text()))

    def ButtonMoveStrAxisClicked(self):
        stroke = float(self.textinManualMoveStr.text())
        point = {"channel": "str_dae", "paramlist": [stroke]}
        steps = self.machine.convert_str_point(point, settings.calibration)
        self.spvcomm.MoveAxisTo("str_dae", steps, int(self.textinManualMoveStrSpeed.text()))

    def ButtonPredefinedPositionEClicked(self):
        self.textinManualMovePhi.setText("27")

    def ButtonPredefinedPositionAClicked(self):
        self.textinManualMovePhi.setText("9")

    def ButtonPredefinedPositionDClicked(self):
        self.textinManualMovePhi.setText("-9")

    def ButtonCalculateCalClicked(self):
        print("Save calibration!")
        cal = self.machine.calculate_new_calibration(settings.calibration_nominal, settings.calibration_positions, settings.calibration)
        print(cal)
        settings.calibration = cal


    def ButtonCalDStringClicked(self):
        self.lblCalDStringIndicator.setStyleSheet("background-color: green")
        settings.calibration_positions["posx1"] = self.machine.machine_state["posx_dae_pos"]
        settings.calibration_positions["posy1"] = self.machine.machine_state["posy_dae_pos"]
        settings.calibration_nominal["r1"] = float(self.textinCalDStringDistance.text())
        settings.calibration_nominal["phi1"] = float(self.textinCalDStringAngle.text())

    def ButtonCalAStringClicked(self):
        self.lblCalAStringIndicator.setStyleSheet("background-color: green")
        settings.calibration_positions["posx2"] = self.machine.machine_state["posx_dae_pos"]
        settings.calibration_positions["posy2"] = self.machine.machine_state["posy_dae_pos"]
        settings.calibration_nominal["r2"] = float(self.textinCalAStringDistance.text())
        settings.calibration_nominal["phi2"] = float(self.textinCalAStringAngle.text())

    def ButtonCalStrMinClicked(self):
        self.lblCalStrMinIndicator.setStyleSheet("background-color: green")
        settings.calibration_positions["str1"] = self.machine.machine_state["str_dae_pos"]
        settings.calibration_nominal["str_mm1"] = float(self.textinCalStrMin.text())

    def ButtonCalStrMaxClicked(self):
        self.lblCalStrMaxIndicator.setStyleSheet("background-color: green")
        settings.calibration_positions["str2"] = self.machine.machine_state["str_dae_pos"]
        settings.calibration_nominal["str_mm2"] = float(self.textinCalStrMax.text())

    def UartReceiveEvent(self, data):
        print("Something has been received")
        self.SetUartStatusIndicator("connected")
        tags = self.spvcomm.DecodePacket(data)
        print(tags)

        self.HandDatapointsToSPV(tags)
        self.machine.UpdateMachineStatus(tags)
        self.UpdateMachineStatusLabels(self.machine.machine_state)


    def UpdateMachineStatusLabels(self, machine_status):
        self.lblPOSXDAEPos.setText(str(self.machine.machine_state["posx_dae_pos"]))
        self.lblPOSYDAEPos.setText(str(self.machine.machine_state["posy_dae_pos"]))
        self.lblSTRDAEPos.setText(str(self.machine.machine_state["str_dae_pos"]))

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
            self.spvcomm.SPVSendCommand("sendDatapoints", data)

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

    def StartAutoRefreshTimer(self):
        milliseconds = int(self.textinMachineStatusUpdateInterval.text())
        self.AutoMachineUpdateTimer = threading.Timer(milliseconds / 1e3, self.AutoRefreshCallback)
        self.AutoMachineUpdateTimer.start()

    def AutoRefreshCallback(self):
        self.spvcomm.SPVSendCommand("getMachineStatus", None)
        if self.AutoMachineUpdateRunning == 1:
            self.StartAutoRefreshTimer()


app = QtWidgets.QApplication(sys.argv)
window = Ui()
app.exec_()

