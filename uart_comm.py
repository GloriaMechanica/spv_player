#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 23 18:55:51 2020

@author: josef
"""
import serial
import serial.tools.list_ports


import PyQt5.QtCore
import time
import settings
import threading
import traceback, sys

from settings import SPVChannelNumbers


class SPVUartConnection:
    def __init__(self, callback):
        self.settings = settings.Settings()
        self.isconnected = False
        self.outgoing_packet_counter = 0
        self.uart_timeout_timer = None
        self.waiting_for_response = 0
        self.resend_counter = 0
        self.last_command = None # used to keep the command in case it needs to be resent
        self.last_data = None # used to keep the data in case it needs to be resent
        self.serial_con = None
        self.threadpool = PyQt5.QtCore.QThreadPool()
        self.poller = None
        self.callback_receive = callback["receive_handler"]
        self.callback_error = callback["error_handler"]

    def getConnectState(self):
        return self.isconnected

    # tries to connect to a com port
    # port - string-like descriptor which port (e.g. "COM1")
    def connectCOMPort(self, port):
        self.serial_con = OpenPort(port, self.settings.baudrate)
        if not (self.serial_con is None):
            self.isconnected = True
            self.StartUartPollingThread(self.serial_con, self.settings.uart_poll_interval)
        return self.serial_con

    def disconnectCOMPort(self):
        self.StopUartPollingThread()
        self.isconnected = False
        ClosePort(self.serial_con)
        self.serial_con = None

    def DecodePacket(self, data):
        # The packet is ok, so we can decode its contents.
        data_length = int.from_bytes(data[2:4], 'big') - self.settings.minimal_packet_length
        print("Databytes unpacket: " + str(data_length))
        result = self.SplitDecodeTLV(data[6:(data_length + 6)])
        return result

    def SplitDecodeTLV(self, data):
        total_length = len(data)
        result = []
        ptr = 0
        while ptr < total_length:
            cmd = data[ptr]
            command_string = settings.SPVAnswerTagsLookup[cmd]
            length = data[ptr + 1]
            datum = data[ptr + 2:ptr + 2 + length]
            if command_string == "SoftwareVersion" and length == settings.SPVAnswerTags[command_string][1]:
                id1 = datum[0]
                id2 = datum[1]
                result.append({"tag": command_string, "id1": id1, "id2": id2})
            elif command_string == "CurrentSystemTime" and length == settings.SPVAnswerTags[command_string][1]:
                systime = int.from_bytes(datum, 'little')
                result.append({"tag": command_string, "time":systime})
            elif command_string == "TimeRunning" and length == settings.SPVAnswerTags[command_string][1]:
                running = datum[0]
                result.append({"tag": command_string, "running":running})
            elif command_string == "DatapointsMissing" and length == settings.SPVAnswerTags[command_string][1]:
                channel_nr = datum[0]
                missing = datum[1]
                result.append({"tag": command_string, "channel":channel_nr, "missing":missing})
            ptr = ptr + length + 2
        return result

    def UartCheckPacket(self, data):
        length = len(data)
        print("Check packet of length " + str(length))

        if length < self.settings.minimal_packet_length:
            print("Packet smaller minimal length!")
            return settings.UartPacketErrors.packetTooShort
        if data[0:2] != self.settings.packet_UID:
            print("UID invalid!")
            return settings.UartPacketErrors.packetUIDError

        expected_length = int.from_bytes(data[2:4], 'big')
        print("Expected length: " + str(expected_length))
        if expected_length < length:
            print("Real packet length smaller than expected.")
            return settings.UartPacketErrors.packetTooShort
        elif expected_length > length:
            print("Real packet length bigger than expected.")
            return settings.UartPacketErrors.packetTooLong
        # ignore packet counter for now...
        acknowledge = data[5]
        if acknowledge != self.settings.ack:
            print("SPV sent NACK!")
            return settings.UartPacketErrors.packetNACK

        crc_calc = crc16(data, length - 2)
        crc_received = int.from_bytes(data[(length - 2):length], 'big')
        if crc_calc != crc_received:
            print("CRC of received package flawed!")
            return settings.UartPacketErrors.packetCRCError
        return settings.UartPacketErrors.packetCorrect

    # This function returns a byte array that can be packed as data to the sendDatapoints command
    # it takes the handle of a channel and the number of datapoints that it should pack into a byte array
    def PrepareChannelDatapoints(self, channel, number):
        data = bytearray()
        obtained_number = 0
        block = channel.getNextDatapoints(number)
        if block is not None:
            obtained_number = len(block)
            data.extend(channel.getChannelNumber().to_bytes(1, 'little'))
            data.extend(len(block).to_bytes(1, 'little'))
            for point in block:
                data.extend(point["timediff"].to_bytes(4, 'little'))
                data.extend(point["pos"].to_bytes(4, 'little', signed=True))
        return [obtained_number, data]

    def MoveAxisTo(self, channel_descriptor, pos, speed):
        print("Want to channel axis " + channel_descriptor + " to pos=" + str(pos))
        data = bytearray()
        channel_nr = SPVChannelNumbers[channel_descriptor]
        data.extend(channel_nr.to_bytes(1, "little"))
        data.extend(pos.to_bytes(2, "little"))
        data.extend(speed.to_bytes(1, "little"))
        self.UartSendCommand("moveChannelTo", data)

    # This is the command to use when you want to send a command to the SPV
    def UartSendCommand(self, command, data):
        self.resend_counter = 0
        self.UartTransmitCommand(command, data)
        self.StartUartTimeout()

    def UartResendCommand(self):
        self.UartTransmitCommand(self.last_command, self.last_data)
        self.StartUartTimeout()

    # This function is only used internally in this class
    def UartTransmitCommand(self, command, data):
        tempdata = bytearray(b'\xCA\xFE')  # UID
        if data is not None:
            length = len(data) + 8
        else:
            length = 8

        if command == "getStatus":
            cmdbyte = b'\x00'
        elif command == "requestChannelFill":
            cmdbyte = b'\x02'
        elif command == "sendDatapoints":
            cmdbyte = b'\x03'
        elif command == "startPlaying":
            cmdbyte = b'\x04'
        elif command == "stopPlaying":
            cmdbyte = b'\x05'
        elif command == "clearChannels":
            cmdbyte = b'\x06'
        elif command == "moveChannelTo":
            cmdbyte = b'\x09'
        else:
            cmdbyte = b'\xFF'  # invalid
        tempdata.extend(length.to_bytes(2, "big"))
        tempdata.extend(self.outgoing_packet_counter.to_bytes(1, "big"))
        tempdata.extend(cmdbyte)
        if data is not None:
            tempdata.extend(data)
        crcval = crc16(tempdata, len(tempdata))
        tempdata.extend(crcval.to_bytes(length=2, byteorder='big'))
        self.serial_con.write(tempdata)
        self.last_command = command  # store in case it needs to be resent
        self.last_data = data
        print("Send: CRC=" + hex(crcval) + " length=" + str(length))

    def UartTimeoutExpire(self):
        print("Expected response form SPV not received!")
        if self.resend_counter < self.settings.resend_tries:
            self.resend_counter = self.resend_counter + 1
            self.UartResendCommand()
            print("Resending command.")
        else:
            print("Exceeded resend tries!")
            self.callback_error("Timeout expire!")
        self.waiting_for_response = 0

    def StartUartTimeout(self):
        # Timeout until the response (Ack/Nack) should arrive from the SPV
        self.waiting_for_response = 1
        self.uart_timeout_timer = threading.Timer(self.settings.responseTimeout / 1e3, self.UartTimeoutExpire)
        self.uart_timeout_timer.start()

    def UartReceivedData(self, data):
        check = self.UartCheckPacket(data)
        if self.waiting_for_response == 1 and check == settings.UartPacketErrors.packetCorrect:
            self.uart_timeout_timer.cancel()
            self.waiting_for_response = 0
        print("Check result: " + str(check))
        self.callback_receive(data)

    def StartUartPollingThread(self, serial_con, response_timeout):
        self.poller = UartReceiveThread(serial_con, response_timeout)
        self.poller.signals.received_data.connect(self.UartReceivedData)
        self.threadpool.start(self.poller)

    def StopUartPollingThread(self):
        if self.poller is not None:
            self.poller.exit()
        self.poller = None
# ----------------------------------------------------------

def GetPorts(): 
    ports = serial.tools.list_ports.comports()
    ports_list = []
    for i in ports:
        ports_list.append(i.device)
    if (ports_list == 0):
        ports_list.append("")
    return ports_list

def OpenPort(port, baud): 
    con = None
    try:
        con = serial.Serial(port, baud, bytesize=serial.EIGHTBITS, timeout=None)
    except serial.SerialException: 
        print("Could not open port!")
    return con
    
def ClosePort(con):
    try: 
        con.close()
    except: 
        print("Serial port error!")    
        
def Writeln(con, string):
    try:
        con.write(string.encode('utf-8'))
        con.write("\n".encode('utf-8'))
        return True
    except serial.SerialException:
        print("Serial connection write error!")
        return False
    
def Readln(con):
    retstr = ""
    raw = 0
    try:
        raw = con.readline()
        raw = raw[:raw.find(ord('\n'))]
        if len(raw) > 0:
            retstr = raw.decode('utf-8')  
        else:
            retstr = "bla"
        print("Return: " + str(retstr))
    except serial.SerialException:
        print("Error reading from serial connection!")
    return retstr

# from Stackexchange, slightly modified:
# https://stackoverflow.com/questions/35205702/calculating-crc16-in-python
def crc16(data : bytearray, length):
    if data is None and length > len(data):
        return 0
    crc = 0xFFFF
    for i in range(0, length):
        crc ^= data[i] << 8
        for j in range(0,8):
            if (crc & 0x8000) > 0:
                crc =(crc << 1) ^ 0x1021
            else:
                crc = crc << 1
    return crc & 0xFFFF



# signal which is generated when the thread received data
class WorkerSignals(PyQt5.QtCore.QObject):
    #define multiple signals here if neccessary
    received_data = PyQt5.QtCore.pyqtSignal(object)


class UartReceiveThread(PyQt5.QtCore.QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, serial_con, poll_interval, *args, **kwargs):
        super(UartReceiveThread, self).__init__()
        self._is_running = True
        self.serial_con = serial_con
        self.pollInterval = poll_interval
        self.signals = WorkerSignals()

    @PyQt5.QtCore.pyqtSlot()
    def run(self):
        
        while(self._is_running == True):
            bytes_in_buffer = self.serial_con.inWaiting()
            if (bytes_in_buffer > 0):
                data = self.serial_con.read(size=bytes_in_buffer)
                self.signals.received_data.emit(data)  # Return the result of the processing
            time.sleep(self.pollInterval/1e3) # can maybe be removed at some point to act more responsive
        
    def exit(self): 
        self._is_running = False
        
