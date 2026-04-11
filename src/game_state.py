from enum import Enum

class GameState(Enum):
    INITIAL   = 0
    HELLOSENT = 1
    TOKENSENT = 2
    MATCHED   = 3
    PLAYERING = 4
    DEAD      = 5

