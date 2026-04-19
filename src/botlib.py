
import inspect, os
from enum import Enum

class Action(Enum):
    SHOOT = 2
    ROTATE_LEFT = 3
    ROTATE_LEFT_FINE = 4
    ROTATE_RIGHT = 5
    ROTATE_RIGHT_FINE = 6
    THRUST = 7
    THRUST_FINE = 8

class Result(Enum):
    LOST = -1
    TIE = 0
    WON = 1

def get_storage_directory():
    # the zeroth frame record is this function; the next frame on the stack is the one where we are being called from
    caller_frame = inspect.stack()[1]
    caller_file = caller_frame.filename
    return os.path.dirname(os.path.abspath(caller_file))

