import pygame
from settings import settings
from src.body import Body
from src.luclib import ZEROVECTOR, lengthdir_x, lengthdir_y, roundi

class Bullet(pygame.sprite.Sprite, Body):
    # note: Bullet objects are always about locally-simulated bullets. The ones from a remote player (in online multiplayer) are in game.remotebullets.

    # multiplied with the screen width/height -- set relatively low because players might otherwise wonder why bullets are coming out of nowhere when the shot was just below escape velocity
    MAX_OUT_OF_SCREEN = 0.25

    def __init__(self, playerobj, virtual=False):
        # 'virtual' bullets are used for simulating where a bullet *would* go, e.g. to draw an aim guide / expected trajectory line.
        # We do not store who the bullet belonged to because it does not matter: whoever collides with it gets damaged. The playerobj parameter is just for initial position and vector.

        pygame.sprite.Sprite.__init__(self)

        x = playerobj.pos.x + lengthdir_x(playerobj.rotatedMaxSize, playerobj.angle)
        y = playerobj.pos.y + lengthdir_y(playerobj.rotatedMaxSize, playerobj.angle)
        if settings['Bullet.relspeed'].val:
            speed = pygame.math.Vector2(playerobj.speed)
        else:
            speed = ZEROVECTOR
        Body.__init__(self, pos=pygame.math.Vector2(x, y), speed=speed, mass=settings['Bullet.mass'].val)

        self.speed.x += lengthdir_x(settings['Bullet.speed'].val, playerobj.angle)
        self.speed.y += lengthdir_y(settings['Bullet.speed'].val, playerobj.angle)
        self.virtual = virtual

        if not self.virtual:
            # self.rect is only used in drawing code
            self.rect = pygame.rect.Rect(0, 0, settings['Bullet.size'].val, settings['Bullet.size'].val)

    def advance(self, screensize):
        # Returns whether it should be removed (out of screen, fell into gravity well; no health-bearing-object collisions)

        separation = super().advance()

        if separation < settings['Bullet.size'].val:
            return True

        if not self.virtual:
            self.rect.center = (roundi(self.pos.x), roundi(self.pos.y))

        if self.pos.x < -(screensize[0] / 2) - ((screensize[0] / 2) * Bullet.MAX_OUT_OF_SCREEN) or self.pos.x > (screensize[0] / 2) + (screensize[0] / 2 * Bullet.MAX_OUT_OF_SCREEN) \
        or self.pos.y < -(screensize[1] / 2) - ((screensize[1] / 2) * Bullet.MAX_OUT_OF_SCREEN) or self.pos.y > (screensize[1] / 2) + (screensize[1] / 2 * Bullet.MAX_OUT_OF_SCREEN):
            return True

        return False

