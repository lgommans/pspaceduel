import random
import src.botlib as botlib

def reset(playerobj):
    pass

def step(game):
    if random.randint(0, 1) == 1:
        return []

    action = random.choice(list(botlib.Action))
    return [action]

