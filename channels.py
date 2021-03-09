# The absolute time is only kept internally to the channelstructure
class ChannelStructure:
    def __init__(self):
        print("Constructed")
        self.currentChannelTime = -1 # always points at the last element that has been executed.
        self.buffer = [] # buffer contains : [{"timestamp":1234, "timediff":bla, "value 1":456, "value2":789, ...}, {...}]

    def getNextDatapoints(self, number):
        nr = min(number, self.getNumberOfRemainingDatapoints())
        if nr == 0:
            return None

        first_element = self.getIndexOfLastExecutedDatapoint()+1
        last_element = first_element+nr-1
        datapoints = []
        for d in self.buffer[first_element:(last_element+1)]:
            datapoints.append(removekey(d, "timestamp"))
        self.currentChannelTime = self.buffer[last_element]["timestamp"]
        return datapoints

    def resetTimeToStart(self):
        self.currentChannelTime = -1 # negative start time meaning not even the first element has been executed

    def setTimeTo(self, time):
        self.currentChannelTime = time

    def getTimeOfLastExecutedDatapoint(self):
        return self.currentChannelTime

    # Returns how many datapoints are available that have not been executed
    def getNumberOfRemainingDatapoints(self):
        last_sent_element = self.getIndexOfLastExecutedDatapoint()
        return len(self.buffer) - last_sent_element - 1

    # Returns the index of the datapoint that has been transmitted the last time.
    # Returns -1 if no element was executed.
    def getIndexOfLastExecutedDatapoint(self):
        last_sent_element = -1
        for idx, datapoint in enumerate(self.buffer):
            if datapoint["timestamp"] == self.currentChannelTime:
                last_sent_element = idx
                break
        return last_sent_element

    # datapoint list should be of type [{"timediff":bla, "value 1":456, "value2":789, ...}, {...}]
    def appendDatapoints(self, datapoint_list):
        if len(self.buffer) == 0:
            last_absolute_time = 0
        else:
            last_absolute_time = self.buffer[-1]["timestamp"]

        for datapoint in datapoint_list:
            new_datapoint = datapoint
            new_datapoint.update({"timestamp":(last_absolute_time+datapoint["timediff"])})
            self.buffer.append(new_datapoint)
            last_absolute_time = self.buffer[-1]["timestamp"]

def removekey(d, key):
    r = dict(d)
    del r[key]
    return r