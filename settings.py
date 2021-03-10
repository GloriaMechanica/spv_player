import numpy as np

class Settings:
    minimal_packet_length = 8
    baudrate = 115200
    uart_timeout = 10
    spv_receive_buffer_length = 1024
    responseTimeout = 500 #ms If no response from the SPV is recieved within, its an error
    uart_poll_interval = 200 # ms: UART checked for new data in this interval
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
SPVAnswerTagsLookup = dict(zip(list(np.array(list(SPVAnswerTags.values()))[:, 0]), SPVAnswerTags.keys()))