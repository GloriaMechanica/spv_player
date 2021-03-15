#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np


class Machine_SPV:

    def __init__(self):
        print("Init machine")

    """
    PolarToangle(): 
        Transforms a pair of machine coordinates for POSX and POSY axis to 
        a polar representation with radius and angle. 
    
        Rphi = [R, phi] Radius in mm, phi in radian
        base: dictionary with origins and radii of both positioning levers
    
        returns: [alpha_x, alpha_y]: angles in radian
    """
    def PolarToAngle(Rphi, base):
        x_left = base["posx_x"]
        y_left = base["posx_y"]
        r_left = base["posx_r"]
        x_right = base["posy_x"]
        y_right = base["posy_y"]
        r_right = base["posy_r"]
        roller_r = base["roller_r"]

        R = Rphi[0] - roller_r
        G = Rphi[1] + np.pi / 2
        x_input = R * np.cos(G)
        y_input = R * np.sin(G)

        # Coefficient vector for quadratic equation to get parameter for left instance
        coeff_left = [pow(x_input, 2) + pow(y_input, 2),
                      -2 * y_input * (x_input - x_left) + 2 * x_input * (y_input - y_left),
                      pow((x_input - x_left), 2) + pow((y_input - y_left), 2) - pow(r_left, 2)]

        # Coefficient vector for quadratic equation to get parameter for right instance
        coeff_right = [pow(x_input, 2) + pow(y_input, 2),
                       -2 * y_input * (x_input - x_right) + 2 * x_input * (y_input - y_right),
                       pow((x_input - x_right), 2) + pow((y_input - y_right), 2) - pow(r_right, 2)]

        solution_left = np.roots(coeff_left)
        solution_right = np.roots(coeff_right)

        if sum(np.iscomplex(solution_right)) or sum(np.iscomplex(solution_left)):
            print("##### ERROR: There is no real solution for the given input #####")
            return False

        intersect_left = [[-y_input * solution_left[0] - x_left + x_input,
                           x_input * solution_left[0] - y_left + y_input],
                          [-y_input * solution_left[1] - x_left + x_input,
                           x_input * solution_left[1] - y_left + y_input]]

        intersect_right = [[-y_input * solution_right[0] - x_right + x_input,
                            x_input * solution_right[0] - y_right + y_input],
                           [-y_input * solution_right[1] - x_right + x_input,
                            x_input * solution_right[1] - y_right + y_input]]

        angles_left = [np.arctan2(h[1], h[0]) for h in intersect_left]
        angles_right = [np.arctan2(h[1], -h[0]) for h in intersect_right]
        angle_left = min(angles_left, key=abs)
        angle_right = min(angles_right, key=abs)

        if np.abs(angle_left) > np.pi / 2 and np.abs(angle_right) > np.pi / 2:
            print("##### ERROR: Angle out of range #####")
            return False

        return [angle_left, angle_right]


    """
    MachineToPolar(): 
        Transforms a pair of machine coordinates for POSX and POSY axis to 
        a polar representation with radius and angle. 
    
        alpha = [alpha_x, alpha_y]: alpha_x and alpha_y are lever angles in radian
        base: dictionary with origins and radii of both positioning levers
    
        returns: [R, phi]: R in mm, phi in radian
    """
    def AngleToPolar(angles, base):
        alpha_l = angles[0]  # angle for posx axis, in degrees
        alpha_r = angles[1]  # angle for posy axis, in degrees
        U_l = np.array([base["posx_x"], base["posx_y"]])  # pivot point of posx axis
        U_r = np.array([base["posy_x"], base["posy_y"]])  # pivot point of posy axis
        r_l = base["posx_r"]  # radius of posx lever
        r_r = base["posy_r"]  # radius of posy lever
        roller_r = base["roller_r"]

        # intersection points
        S_l = U_l + np.array([r_l * np.cos(alpha_l), r_l * np.sin(alpha_l)])
        S_r = U_r + np.array([-r_r * np.cos(alpha_r), r_r * np.sin(alpha_r)])

        # line
        k_t = S_l - S_r
        k_r = np.array([-k_t[1], k_t[0]])

        A = np.ndarray([list(k_r), list(k_t)])
        t = np.linalg.solve(A, S_l)

        P = k_r * t[0]

        R = np.sqrt(np.power(P[0], 2) + np.power(P[1], 2))
        phi = np.arctan2(P[1], P[0]) - np.pi / 2
        R += roller_r

        return [R, phi]

    def convert_str_point(self, input_point, calibration):
        return int(int(input_point["paramlist"][1])*calibration["str_steps_per_mm"]) + calibration["str_steps_offset"]

    def convert_pos_point(self, input_point, calibration):
        if (input_point["pos_dae"]):
            input_radius = int(input_point["paramlist"][0])
            input_angle = int(input_point["paramlist"][1])
            radius = input_radius + calibration["nominal_string_radius"]
            angle = input_angle / 180 * np.pi
            ret = self.PolarToAngle([radius, angle], calibration)
            if ret is not False:
                [angle_x, angle_y] = ret
            else:
                print("Polar to machine conversion error!")

            steps_x = int(angle_x * calibration["posx_steps_per_degree"]) + calibration["posx_steps_offset"]
            steps_y = int(angle_y * calibration["posy_steps_per_degree"]) + calibration["posy_steps_offset"]
            return [steps_x, steps_y]
        else:
            print("GDA string not supported yet!")
            return None


    def convert_note_point(self, input_point, calibration):
        print("bla")

