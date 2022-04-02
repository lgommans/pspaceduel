#!/usr/bin/env python3

import math, time
from inspect import currentframe

def lengthdir_x(length, direction):
    return length * math.cos((direction + 90) / 180 * math.pi)


def lengthdir_y(length, direction):
    return length * math.sin((direction - 90) / 180 * math.pi)


starttime = time.time()
def timeme(out=True, th=0):  # params: show output; threshold above which it should be shown
    global starttime
    now = time.time()
    cf = currentframe()
    ln = cf.f_back.f_lineno  # line number of the parent stack frame
    if out:
        td = (now - starttime) * 1000000
        if th < td:
            print(ln, td, 'µs')
    starttime = now

