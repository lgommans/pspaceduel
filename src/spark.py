import random
import pygame
from settings import prefs

class Spark:
    def __init__(self, pos):
        try:
            Spark.IMAGE
        except AttributeError:
            Spark.IMAGE = pygame.image.load(prefs['Spark.graphic']).convert_alpha()

        self.pos = pygame.math.Vector2(pos)
        self.lifespan = random.randint(*prefs['Spark.lifespan'])
        self.angle = random.randint(0, 360)
        self.rotation = random.randint(*prefs['Spark.rotation']) * (-1 if random.randint(1, 2) == 1 else 1)
        self.img = Spark.IMAGE

    def advance(self, screen):
        # returns True if it needs to be destroyed

        self.lifespan -= 1
        if self.lifespan <= 0:
            return True

        self.pos.x += random.randint(*prefs['Spark.movement']) * (-1 if random.randint(1, 2) == 1 else 1)
        self.pos.y += random.randint(*prefs['Spark.movement']) * (-1 if random.randint(1, 2) == 1 else 1)
        self.angle += self.rotation

        self.img = pygame.transform.rotate(Spark.IMAGE, self.angle)

