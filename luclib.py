#!/usr/bin/env python3

import math

def lengthdir_x(length, direction):
    return length * math.cos((direction + 90) / 180 * math.pi)

def lengthdir_y(length, direction):
    return length * math.sin((direction - 90) / 180 * math.pi)

