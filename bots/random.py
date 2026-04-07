import random
import botlib

def reset():
    pass

def step(game):
    if random.randint(0, 1) == 1:
        return []

    action = random.choice(list(botlib.Action))
    return [action]

