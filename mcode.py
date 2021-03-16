import numpy as np
import settings

class McodeReader:
    def __init__(self, calibration):
        self.calibration = calibration # holding all calibration for conversion.

    def parseFile(self, path):
        file = open(path, "r")
        lines_raw = file.readlines()
        symbol_dict = {}

        # first kill all commends
        lines_raw = [l.split("//")[0] for l in lines_raw]
        lines_raw_nr = list(enumerate(lines_raw, 1))

        # Preprocessor
        # 1. find symbols
        lines_prep = []
        lines_prep_nr = []
        found_begin = 0
        for idx,line in enumerate(lines_raw):
            l = line.strip() # remove leading/trailing whitespaces/linebreaks
            if len(l) > 0:
                if l[0] == "#":
                    # This is a preprocessor command
                    parts = l.split(" ")
                    parts = [p.strip() for p in parts]
                    if parts[0]=="#define":
                        symbol_dict.update({parts[1]:int(parts[2])})
                    elif parts[0]=="#begin":
                        found_begin = 1
                elif found_begin==1:
                    lines_prep.append(l)
                    lines_prep_nr.append(lines_raw_nr[idx]) # Save line numbers to be able to give error messages
        print(symbol_dict)

        lines_data = []
        lines_data_nr = []
        # 2. replace symbols
        for idx,line in enumerate(lines_prep):
            temp = line
            for d in symbol_dict:
                temp = temp.replace(d, str(symbol_dict[d]))
            if temp.find("$")>=0:
                # There are still labels left. This should not be the case
                bad_key = temp[temp.find("$"):].split(" ")[0]
                bad_key_position = lines_prep_nr[idx]
                print("Unknown label on line " + str(bad_key_position) + "!")
                return None
            else:
                lines_data.append(temp)
                lines_data_nr.append(lines_prep[idx])

        # Main data processing

        # Unravelling the time
        buffer = []
        list_abstime = []
        last_time = 0
        current_time = 0
        for idx,line in enumerate(lines_data):
            if line[0] == "!":
                # This is a frame point
                temp = (line[1:]).split(" ")
                if len(temp) < 3:
                    print("Wrong datapoint on line " + str(lines_data_nr[idx]))
                    return None
                else:
                    time_spec = temp[0]
                    channel_spec = temp[1]

                if time_spec.find("+")>=0:
                    # this is relative time spec
                    current_time = last_time + int(time_spec)
                elif time_spec.find("-")>=0:
                    print("Backward time specification is not allowed with frame points! on line " + str(lines_data_nr[idx]))
                    return None
                else:
                    # Must be absolute time spec
                    current_time = int(time_spec)

                if current_time < last_time:
                    print("Time runs in reverse at line " + str(lines_data_nr[idx]))

                # Now work through the buffer of intermediate commands
                for element in buffer:
                    parts = element.split(" ")
                    element_time_spec = parts[0]
                    element_channel_spec = parts[1]
                    if element_time_spec.find("+")>=0:
                        element_time = last_time + int(element_time_spec)
                    elif element_time_spec.find("-")>=0:
                        element_time = current_time + int(element_time_spec)
                    else:
                        element_time = int(time_spec)
                    list_abstime.append({"abstime": element_time, "channel": element_channel_spec, "paramlist": parts[2:]})

                list_abstime.append({"abstime": current_time, "channel": channel_spec, "paramlist": temp[2:]})
                # at last, update the time till the next frame point comes
                last_time = current_time
                buffer = []
            else:
                buffer.append(line)
        # Commands could
        list_abstime.sort(key=lambda x: x["abstime"])
        return list_abstime

    def getLineNumber(self, string_list, string):
        for idx, line in enumerate(string_list):
            if line.find(string)>=0:
                return idx + 1 # Line numbers start at 1, but python lists at 0

    def pushMcodeDataToChannels(self, data, channels_handle, machine_handle):
        # Split the data to an individual list containing only points of one axis
        axis_buffers = []
        for idx,axis in enumerate(settings.SPVMcodeAxisList.keys()):
            axis_buffers.append([])

        for d in data:
            axis_buffers[settings.SPVMcodeAxisList[d["channel"]]].append(d)

        print("Split axis buffers:")
        for buf in axis_buffers:
            print(buf)

        for idx,axis in enumerate(axis_buffers):
            if len(axis) is not 0:
                last_time = -1000 # TODO: do this properly with init!
                if idx >= settings.SPVMcodeAxisList["g_note"] and idx <= settings.SPVMcodeAxisList["e_note"]:
                    for point in axis:
                        note = machine_handle.convert_note_point(point, self.calibration)
                        timediff = point["abstime"] - last_time
                        last_time = point["abstime"]
                        channels_handle[settings.SPVMcodeAxisListLookup[idx]].appendDatapoints(
                            [{"timediff": timediff, "note": note}])
                elif idx == settings.SPVMcodeAxisList["pos_dae"]:
                    for point in axis:
                        print(point)
                        [stepsx, stepsy] = machine_handle.convert_pos_point(point, self.calibration)
                        timediff = point["abstime"] - last_time
                        last_time = point["abstime"]
                        channels_handle["posx_dae"].appendDatapoints(
                            [{"timediff": timediff, "pos": stepsx}])
                        channels_handle["posy_dae"].appendDatapoints(
                            [{"timediff": timediff, "pos": stepsy}])
                elif idx == settings.SPVMcodeAxisList["str_dae"]:
                    for point in axis:
                        steps = machine_handle.convert_str_point(point, self.calibration)
                        timediff = point["abstime"] - last_time
                        last_time = point["abstime"]
                        channels_handle["str_dae"].appendDatapoints(
                            [{"timediff": timediff, "pos": steps}])
                    #TODO: Add more axis here


