import random
import src.botlib as botlib

class Bot:
    def __init__(self, player):
        self.player = player

    def reset(self):
        pass

    def step(self, game):
        if random.randint(0, 1) == 1:
            return []

        action = random.choice(list(botlib.Action))
        return [action]

    def gameover(self, result):
        pass

