# spv_player
This repo contains a PyQt5 project which serves to interface to the SPV. The .ui file is created with Qt 5 Designer and imported in the main pyhton file, spvplayer.py. 

The intent is to have a tool which reads in text-based m-code does the coordinate transformations and prepares the byte-based channel data for the SPV. Moreover, it handles the uart connection and provides the SPV with data upon request for the individual channels. A user interface for calibrating the axis will also be part of the game. 

Current features: 
* Accessing the COM port via PySerial lib, reading data from the port in a separate thread in order not to block the GUI
