# Copyright (c) 2018 Ultimaker B.V.
# Cura is released under the terms of the LGPLv3 or higher.

from ..Script import Script

from UM.Application import Application #To get the current printer's settings.
from UM.Logger import Logger

class PauseAtTopAndBottom(Script):
    def __init__(self):
        super().__init__()

    def getSettingDataString(self):
        return """{
            "name": "Pause at top and bottom",
            "key": "PauseAtTopAndBottom",
            "metadata": {},
            "version": 2,
            "settings":
            {
                "pause_in_bottom_layer":
                {
                    "label": "Pause in bottom layer",
                    "description": "Whether to pause in the bottom layer",
                    "type": "bool",
                    "default_value": false
                },
                "pause_before_skin_bottom":
                {
                    "label": "Before skin",
                    "description": "Whether to pause in the bottom layer before printing the skin",
                    "type": "bool",
                    "default_value": false,
                    "enabled": "pause_in_bottom_layer"
                },
                "pause_after_skin_bottom":
                {
                    "label": "After skin",
                    "description": "Whether to pause in the bottom layer after printing the skin",
                    "type": "bool",
                    "default_value": false,
                    "enabled": "pause_in_bottom_layer"
                },
                "pause_in_top_layer":
                {
                    "label": "Pause in top layer",
                    "description": "Whether to pause in the top layer",
                    "type": "bool",
                    "default_value": false
                },
                "pause_before_skin_top":
                {
                    "label": "Before skin",
                    "description": "Whether to pause in the top layer before printing the skin",
                    "type": "bool",
                    "default_value": false,
                    "enabled": "pause_in_top_layer"
                },
                "pause_after_skin_top":
                {
                    "label": "After skin",
                    "description": "Whether to pause in the top layer after printing the skin",
                    "type": "bool",
                    "default_value": false,
                    "enabled": "pause_in_top_layer"
                },
                "head_park_x":
                {
                    "label": "Park Print Head X",
                    "description": "What X location does the head move to when pausing.",
                    "unit": "mm",
                    "type": "float",
                    "default_value": 190
                },
                "head_park_y":
                {
                    "label": "Park Print Head Y",
                    "description": "What Y location does the head move to when pausing.",
                    "unit": "mm",
                    "type": "float",
                    "default_value": 190
                },
                "retract_before_pause":
                {
                    "label": "Retract filament before pausing",
                    "description": "Use machine setting for retraction before pausing",
                    "type": "bool",
                    "default_value": true
                }
            }
        }"""

    def generate_pause(self, is_griffin, current_x, current_y, current_z, current_e):

        park_x = self.getSettingValueByKey("head_park_x")
        park_y = self.getSettingValueByKey("head_park_y")

        retract_before_pause = self.getSettingValueByKey("retract_before_pause")

        pause_gcodes = [
            ";TYPE:CUSTOM",
            ";added code by post processing",
            ";script: PauseAtTopAndBottom.py"
        ]

        if not is_griffin:
            if retract_before_pause:
                pause_gcodes.append(self.putValue(G = 10))

            # Move the head away
            pause_gcodes.append(self.putValue(G = 1, Z = current_z + 1, F = 4500))

            # Park the print head
            pause_gcodes.append(self.putValue(G = 1, X = park_x, Y = park_y, F = 4500))

            if current_z < 70:
                pause_gcodes.append(self.putValue(G = 1, Z = 70, F = 4500))

        # Wait till the user continues printing
        pause_gcodes.append(self.putValue(M = 0) + ";Do the actual pause")

        if not is_griffin:

            # Move the head back
            pause_gcodes.append(self.putValue(G = 1, Z = current_z + 1, F = 4500))
            pause_gcodes.append(self.putValue(G = 1, X = current_x, Y = current_y, F = 4500))

            if retract_before_pause:
                pause_gcodes.append(self.putValue(G = 11))
            pause_gcodes.append(self.putValue(G = 1, Z = current_z, F = 4500))
            pause_gcodes.append(self.putValue(G = 92, E = current_e))

        return pause_gcodes

    def execute(self, data: list):
        """data is a list. Each index contains a layer"""

        pause_in_bottom_layer = self.getSettingValueByKey("pause_in_bottom_layer")
        pause_before_skin_bottom = self.getSettingValueByKey("pause_before_skin_bottom")
        pause_after_skin_bottom = self.getSettingValueByKey("pause_after_skin_bottom")
        
        pause_in_top_layer = self.getSettingValueByKey("pause_in_top_layer")
        pause_before_skin_top = self.getSettingValueByKey("pause_before_skin_top")
        pause_after_skin_top = self.getSettingValueByKey("pause_after_skin_top")

        is_griffin = False

        current_x = 0
        current_y = 0
        current_z = 0
        current_e = 0

        pauses_to_add = []


        for index, layer in enumerate(data):
            lines = layer.split("\n")

            is_bottom_layer = False
            in_skin_lines = False

            # Scroll each line of instruction for each layer in the G-code
            for line_index, line in enumerate(lines):
                if ";FLAVOR:Griffin" in line:
                    is_griffin = True

                if self.getValue(line, "X") is not None:
                    current_x = self.getValue(line, "X")

                if self.getValue(line, "Y") is not None:
                    current_y = self.getValue(line, "Y")

                if self.getValue(line, "Z") is not None:
                    current_z = self.getValue(line, "Z")

                if self.getValue(line, "E") is not None:
                    current_e = self.getValue(line, "E")

                if ";LAYER:0" == line:
                    is_bottom_layer = True
                    continue

                if is_bottom_layer and ";TYPE:SKIN" in line:
                    in_skin_lines = True
                    if pause_before_skin_bottom:
                        pauses_to_add.append( (index, line_index, current_x, current_y, current_z, current_e) )
                    continue

                if is_bottom_layer and in_skin_lines and line.startswith(";"):
                    if pause_after_skin_bottom:
                        pauses_to_add.append( (index, line_index, current_x, current_y, current_z, current_e) )
                    break

        if pause_in_top_layer:
            top_layer = ''
            top_layer_index = -1
            for index, layer in reversed(list(enumerate(data))):
                top_layer = layer
                top_layer_index = index
                if ";LAYER:" in layer: break
            Logger.log("d", top_layer)
            lines = top_layer.split("\n")

            in_skin_lines = False

            for line_index, line in enumerate(lines):
                if self.getValue(line, "X") is not None:
                    current_x = self.getValue(line, "X")

                if self.getValue(line, "Y") is not None:
                    current_y = self.getValue(line, "Y")

                if self.getValue(line, "Z") is not None:
                    current_z = self.getValue(line, "Z")

                if self.getValue(line, "E") is not None:
                    current_e = self.getValue(line, "E")

                # No more pause if there is only one layer
                if ";LAYER:0" == line:
                    continue

                if ";TYPE:SKIN" in line:
                    in_skin_lines = True
                    if pause_before_skin_top:
                        pauses_to_add.append( (top_layer_index, line_index, current_x, current_y, current_z, current_e) )
                    continue

                if in_skin_lines and line.startswith(";") and pause_after_skin_top:
                    pauses_to_add.append( (top_layer_index, line_index, current_x, current_y, current_z, current_e) )
                    continue           

        for pause in reversed(pauses_to_add):
            pause_layer = data[pause[0]]
            pause_lines = pause_layer.split("\n")
            pause_lines = pause_lines[:pause[1]] + self.generate_pause(is_griffin, pause[2], pause[3], pause[4], pause[5]) + pause_lines[pause[1]:]
            data[pause[0]] = "\n".join(pause_lines)

        return data