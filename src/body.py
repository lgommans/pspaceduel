import math
from settings import settings
from src.luclib import ZEROVECTOR, lengthdir_x, lengthdir_y

class Body:
    GRAVITATIONAL_CONSTANT = 6.6742e-11

    def __init__(self, pos=None, speed=None, mass=None):
        self.pos = pos
        self.speed = speed
        self.mass = mass

    def advance(self):
        # does 2-body Newtonian gravity between itself and the GravityWell
        separation_x = self.pos.x
        separation_y = self.pos.y
        separation_square = (separation_x * separation_x) + (separation_y * separation_y)
        grav_accel = self.mass * settings['GW.mass'].val / separation_square * (settings['Game.timeStep'].val * Body.GRAVITATIONAL_CONSTANT)
        separation = math.sqrt(separation_square)
        dir_x = separation_x / separation
        dir_y = separation_y / separation

        self.speed.x -= grav_accel / self.mass * dir_x
        self.speed.y -= grav_accel / self.mass * dir_y
        self.pos.x += self.speed.x * settings['Game.timeStep'].val
        self.pos.y += self.speed.y * settings['Game.timeStep'].val

        # returns distance from gravity well's surface
        return separation - settings['GW.radius'].val  # GW assumed to be spherical

