import numpy as np
import settings
import matplotlib.pyplot as plt
import datetime

class McodeReader:
    def __init__(self, calibration):
        self.calibration = calibration # holding all calibration for conversion.

    def parseFile(self, path):
        file = open(path, "r")
        lines_raw = file.readlines()
        lines_raw_ = lines_raw
        symbol_dict = {}

        # first kill all commends
        lines_raw = [l.split("//")[0] for l in lines_raw]
        lines_raw_nr = list(enumerate(lines_raw, 1))

        # Preprocessor
        # 1. find symbols
        lines_prep = []
        cmd_list_prep = []
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
                    cmd_list_prep.append({"src_line": idx +1 , "src_cmd": l})
                    lines_prep_nr.append(lines_raw_nr[idx]) # Save line numbers to be able to give error messages
        print(symbol_dict)
        print(cmd_list_prep)

        lines_data = []
        lines_data_nr = []
        # 2. replace symbols
        for idx,line in enumerate(lines_prep):
            temp = line
            for d in symbol_dict:
                temp = temp.replace(d, str(symbol_dict[d]))
                cmd_list_prep[idx]["src_cmd"] = temp
            if temp.find("$")>=0:
                # There are still labels left. This should not be the case
                bad_key = temp[temp.find("$"):].split(" ")[0]
                bad_key_position = lines_prep_nr[idx]
                print("Unknown label on line " + str(bad_key_position) + "!")
                return None
            else:
                lines_data.append(temp)
                lines_data_nr.append(lines_prep[idx])
        print(cmd_list_prep)
        # Main data processing

        # Unravelling the time
        buffer = []
        buffer_ = []
        list_abstime = []
        last_time = 0
        current_time = 0
        for idx,line in enumerate(lines_data):
            if line[0] == "!":
                # This is a frame point
                temp = (line[1:]).split()

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
                for idx_,element in enumerate(buffer):
                    parts = element[0].split()
                    element_time_spec = parts[0]
                    element_channel_spec = parts[1]
                    if element_time_spec.find("+")>=0:
                        element_time = last_time + int(element_time_spec)
                    elif element_time_spec.find("-")>=0:
                        element_time = current_time + int(element_time_spec)
                    else:
                        element_time = int(time_spec)
                    list_abstime.append({"abstime": element_time, "channel": element_channel_spec, "paramlist": parts[2:]})
                    cmd_list_prep[element[1]]["abstime"] = element_time

                list_abstime.append({"abstime": current_time, "channel": channel_spec, "paramlist": temp[2:]})
                cmd_list_prep[idx]["abstime"] = current_time
                # at last, update the time till the next frame point comes
                last_time = current_time
                buffer = []
            else:
                buffer.append([line, idx])
        # add intermediate commands after last point
        for idx_, element in enumerate(buffer):
            parts = element[0].split(" ")
            element_time_spec = parts[0]
            element_channel_spec = parts[1]
            if element_time_spec.find("+") >= 0:
                element_time = last_time + int(element_time_spec)
            elif element_time_spec.find("-") >= 0:
                print("negative relative time spec forbidden after last framepoint! Ignoring!")
            else:
                element_time = int(time_spec)
            list_abstime.append({"abstime": element_time, "channel": element_channel_spec, "paramlist": parts[2:]})
            cmd_list_prep[element[1]]["abstime"] = element_time


        # Commands could
        list_abstime.sort(key=lambda x: x["abstime"])
        print("list_abstime:")
        for le in list_abstime:
            print(le)
        print("cmd_list_prep:")
        for le in cmd_list_prep:
            print(le)
        return list_abstime, cmd_list_prep, lines_raw_

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
                #last_time = -1000 # TODO: do this properly with init!
                last_time = 0
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


    def cmd_list_generator(self, cmd_list_prep):
        line_list = {}
        previous_abstime = -1
        # Generating a list which defines when a set of lines is shown
        for element in cmd_list_prep:
            if previous_abstime != element["abstime"]:
                line_list[element["abstime"]] = [element["src_line"]]
                previous_abstime = element["abstime"]
            else:
                line_list[previous_abstime].append(element["src_line"])

        # Filling out the missing lines with lines not containing commands

        previous_max_line = 0
        for key,lines in line_list.items():
            if previous_max_line < min(lines):
                for i in range(previous_max_line + 1, min(lines)):
                    line_list[key].append(i)
                lines.sort()
            previous_max_line = max(lines)

        print(line_list)

    def plot_channel_business(self, channel_handle):
        print("start plotting timeline")

        fig, ax = plt.subplots(2,1)
        length_time = 0
        ctr = 0
        buf = channel_handle["e_note"].getChannelBuffer()
        if not len(buf) == 0:
            ax[0].axvline(buf[0]["timediff"], 0, 0.25, color="red", label="e_note")
        for point in buf:
            ctr = ctr + int(point["timediff"])
            ax[0].axvline(int(point["timestamp"]), 0, 0.25, color="red")
            ax[0].text(ctr+10, 0.02, str(settings.SPVNoteRangeLookup[point["note"]]))
        length_time = max(length_time, ctr)

        ctr = 0
        buf = channel_handle["posx_dae"].getChannelBuffer()
        if not len(buf) == 0:
            ax[0].axvline(buf[0]["timediff"], 0.25, 0.5, color="lightgreen", label="posx_dae")
        for point in buf:
            ctr = ctr + int(point["timediff"])
            ax[0].axvline(ctr, 0.25, 0.5, color="lightgreen")
        length_time = max(length_time, ctr)

        ctr = 0
        buf = channel_handle["posy_dae"].getChannelBuffer()
        if not len(buf) == 0:
            ax[0].axvline(buf[0]["timediff"], 0.5, 0.75, color="green", label="posy_dae")
        for point in buf:
            ctr = ctr + int(point["timediff"])
            ax[0].axvline(ctr, 0.5, 0.75, color="green")
        length_time = max(length_time, ctr)

        str_times = []
        str_positions = []
        ctr = 0
        buf = channel_handle["str_dae"].getChannelBuffer()
        if not len(buf) == 0:
            ax[0].axvline(buf[0]["timediff"], 0.75, 1, color="blue", label="str_dae")
        for point in buf:
            ctr = ctr + int(point["timediff"])
            str_times.append(ctr)
            ax[0].axvline(ctr, 0.75, 1, color="blue")
            str_positions.append(int(point["pos"]))
        length_time = max(length_time, ctr)

        width = int(length_time) / 20 # autoscaling width for good readability
        height = 100

        ax[0].grid(True, linestyle='--')
        ax[0].set_xlabel("time (ms)")
        ax[0].legend(loc='upper center', bbox_to_anchor=(1.05, 0.7))
        ax[0].set_xlim(-10, length_time)
        ax[1].plot(str_times, str_positions, color="blue", label="str_dae")
        ax[1].set_xlim(-10, length_time)
        ax[1].grid(True, linestyle='--')

        fig.set_size_inches(width / 25.4, height / 25.4)
        fig.savefig("timeline.pdf", format="pdf", bbox_inches="tight")