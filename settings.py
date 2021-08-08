import numpy as np

# everything in mm, degrees or steps
calibration_old = {"posx_x": -60, "posx_y": 25, "posx_r": 25,
               "posx_steps_offset":600, "posx_steps_per_degree":-8.755,
               "posy_x": 60, "posy_y": 50, "posy_r": 35,
               "posy_steps_offset": 600, "posy_steps_per_degree":-8.755,
               "roller_r": 5, "nominal_string_radius":38,
               "str_steps_offset": 0, "str_steps_per_mm":13,
               "posy_steps_per_degree":10}
calibration = {'posx_x': -60, 'posx_y': 25, 'posx_r': 25,
                'posy_x': 60, 'posy_y': 50, 'posy_r': 35,
                'posx_steps_offset': 507.1526894161782, 'posx_steps_per_degree': -8.755,
               'posy_steps_offset': 230.223071967713, 'posy_steps_per_degree': -8.755,
               'roller_r': 5, 'nominal_string_radius': 38, 'str_steps_offset': -1.0, 'str_steps_per_mm': 12.0}

calibration_positions = {}
calibration_nominal = {}

class Settings:
    minimal_packet_length = 8
    baudrate = 115200
    uart_timeout = 10
    spv_receive_buffer_length = 1024
    responseTimeout = 500 #ms If no response from the SPV is recieved within, its an error
    uart_poll_interval = 10 # ms: UART checked for new data in this interval
    resend_tries = 3 # a command is retried that many times if the SPV responds with a NACK
    packet_UID = bytes(b'\xCA\xFE')
    ack = 0
    maximum_datapoints_per_transfer = np.floor((spv_receive_buffer_length - 36)/8).astype(int) # 36 bytes are for header etc. in worst case, 8 bytes is the longest datapoint (worst case)


testpositions_xy = [500, 	500, 	1550, 	250, 	2000, 	0, 		100, 	0]
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
    "ChannelReady" : [4, 1],
    "AxisStatus" : [5, 4]
    }
SPVAnswerTagsLookup = dict(zip(list(np.array(list(SPVAnswerTags.values()))[:, 0]), SPVAnswerTags.keys()))

# Names and numbers for axis used in M-code. Not the same as the channels on the SPV!
SPVMcodeAxisList = {"g_note":0, "d_note":1, "a_note":2, "e_note":3, "pos_dae":4, "pos_gda":5,
                    "str_dae":6, "str_gda":7, "g_vib":8, "d_vib":9, "a_vib":10, "e_vib":11}
SPVMcodeAxisListLookup = dict(zip(SPVMcodeAxisList.values(), SPVMcodeAxisList.keys()))

# Names and numbers for the channels on the SPV.
SPVChannelNumbers = {
    "g_note" : 0,
    "d_note" : 1,
    "a_note" : 2,
    "e_note" : 3,
    "posx_dae" : 4,
    "posy_dae" : 5,
    "str_dae" : 6,
    "posx_gda" : 7,
    "posy_gda" : 8,
    "str_gda" : 9,
    "g_vib" : 10,
    "g_vib" : 11,
    "g_vib" : 12,
    "g_vib" : 13
}


SPVNoteRange = {
    "g3" : 55,
    "g3#" : 56,
    "a3" : 57,
    "a3#" : 58,
    "b3" : 59,
    "c4" : 60,
    "c4#" : 61,
    "d4" : 62,
    "d4#" : 63,
    "e4" : 64,
    "f4" : 65,
    "f4#" : 66,
    "g4" : 67,
    "g4#" : 68,
    "a4" : 69,
    "a4#" : 70,
    "b4" : 71,
    "c5" : 72,
    "c5#" : 73,
    "d5" : 74,
    "d5#" : 75,
    "e5" : 76,
    "f5" : 77,
    "f5#" : 78,
    "g5" : 79,
    "g5#" : 80,
    "a5" : 81,
    "a5#" : 82,
    "b5" : 83,
    "c6" : 84,
    "c6#" : 85,
    "d6": 86,
    "d6#" : 87,
    "e6" : 88,
    "f6" : 89,
    "f6#" : 90,
    "g6": 91,
    "g6#" : 92,
    "a6" : 93,
    "g_note_min" : 55,
    "g_note_max" : 65,
    "d_note_min" : 62,
    "d_note_max" : 73,
    "a_note_min" : 69,
    "a_note_max" : 80,
    "e_note_min" : 76,
    "e_note_max" : 93
}

SPVNoteRangeLookup = {
    55:"g3",
    56:"g3#",
    57:"a3",
    58:"a3#",
    59:"b3",
    60:"c4",
    61:"c4#",
    62:"d4",
    63:"d4#",
    64:"e4",
    65:"f4",
    66:"f4#",
    67:"g4",
    68:"g4#",
    69:"a4",
    70:"a4#",
    71:"b4",
    72:"c5",
    73:"c5#",
    74:"d5",
    75:"d5#",
    76:"e5",
    77:"f5",
    78:"f5#",
    79:"g5",
    80:"g5#",
    81:"a5",
    82:"a5#",
    83:"b5",
    84:"c6",
    85:"c6#",
    86:"d6",
    87:"d6#",
    88:"e6",
    89:"f6",
    90:"f6#",
    91:"g6",
    92:"g6#",
    93:"a6"
}
