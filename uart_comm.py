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
import traceback, sys

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

    def __init__(self, serial_con, *args, **kwargs):
        super(UartReceiveThread, self).__init__()
        self._is_running = True
        self.serial_con = serial_con
        self.signals = WorkerSignals()

    @PyQt5.QtCore.pyqtSlot()
    def run(self):
        
        while(self._is_running == True):
            bytes_in_buffer = self.serial_con.inWaiting()
            if (bytes_in_buffer > 0):
                data = self.serial_con.read(size=bytes_in_buffer)
                self.signals.received_data.emit(data)  # Return the result of the processing
            time.sleep(0.2)
        
    def exit(self): 
        self._is_running = False
        
"""       
def uart_polling_thread(self, e):
    ticks = 0
    
    # polling the uart input buffer
    while (self._want_abort==0):
        ticks = ticks + 1
        string = Readln(self.serial_con)
        
        return  # found result string
        time.sleep(self.interval)
    
    
        

    def abort(self):
        self._want_abort = 1
            
   """ 


    