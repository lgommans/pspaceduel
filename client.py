#!/usr/bin/env python3

import sys, math, socket, time, struct
import pygame
import mplib
from luclib import *

class Player:
    SCALE = (0.2, 0.2)
    ROTATIONAL_SPEED = 3
    MASS = 100  # kg
    P1_START_X = 200
    P1_START_Y = 400
    P1_START_XSPEED = 4
    P1_START_YSPEED = -2
    P2_START_X = 900
    P2_START_Y = 800
    P2_START_XSPEED = -4
    P2_START_YSPEED = 2
    BATTERY_CAPACITY = 100
    THRUST = 1000  # Newtons

    def __init__(self, n):
        img = pygame.image.load(f'res/player{n}.png')
        rect = img.get_rect()

        self.n = n
        self.img = pygame.transform.scale(img, (int(round(rect.width * Player.SCALE[0])), int(round(rect.height * Player.SCALE[1]))))
        self.rect = self.img.get_rect()
        self.angle = 0
        self.pos = None  # initialized when round starts
        self.speed = None

    def thrust(self):
        self.speed['x'] += lengthdir_x(Player.THRUST * FRAMETIME / Player.MASS, self.angle)
        self.speed['y'] += lengthdir_y(Player.THRUST * FRAMETIME / Player.MASS, self.angle)

    def draw(self, screen):
        blitRotateCenter(screen, self.img, (self.rect.left, self.rect.top), self.angle)

    def rotate(self, direction):  # direction is 1 or -1
        self.angle += direction * Player.ROTATIONAL_SPEED
        self.angle %= 360

    def gravity(self, towards_pos, towards_mass):
        # It is assumed that the 'towards' object is at a fixed position (a gravity well). It will not be updated according to forces felt

        separation_x = self.rect.x - towards_pos[0]
        separation_y = self.rect.y - towards_pos[1]
        separation = math.sqrt(separation_x * separation_x + separation_y * separation_y)
        grav_accel = Player.MASS * towards_mass / (separation * separation) * FTGC
        dir_x = separation_x / separation
        dir_y = separation_y / separation
        self.speed['x'] -= grav_accel / Player.MASS * dir_x
        self.speed['y'] -= grav_accel / Player.MASS * dir_y

    def update(self):
        self.pos['x'] += self.speed['x']
        self.pos['y'] += self.speed['y']
        self.rect.left = self.pos['x']
        self.rect.top = self.pos['y']


def blitRotateCenter(surf, image, pos, angle):
    # this function is CC-BY-SA 4.0 by Rabbid76 from https://stackoverflow.com/a/54714144
    rotated_image = pygame.transform.rotate(image, angle)
    new_rect = rotated_image.get_rect(center=image.get_rect(topleft = pos).center)
    surf.blit(rotated_image, new_rect)


def stopgame(reason, exitstatus=0):
    sock.sendto(mplib.playerquits + reason.encode('ASCII'), SERVER)
    sys.exit(exitstatus)


GAMEVERSION = 1
GRAVITYCONSTANT = 6.6742e-11
SCREENSIZE = (1440, 900)
FPS = 60
FRAMETIME = 1 / FPS
FTGC = FRAMETIME * GRAVITYCONSTANT
SERVER = ('127.0.0.1', 9473)

STATE_HELLOSENT = 1
STATE_TOKENSENT = 2
STATE_MATCHED   = 3
STATE_PLAYERING = 4

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setblocking(0)
sock.sendto(mplib.clienthello, SERVER)
mptoken = None
state = STATE_HELLOSENT
statusmessage = 'Waiting for server initial response...'

pygame.init()
font = pygame.font.SysFont(None, 48)

players = [
    Player(1),
    Player(2),
]

gravitywell = pygame.image.load(f'res/sun.png')
gravitywell_mass = 1e16
gravitywellrect = gravitywell.get_rect()
gravitywellrect.left = (SCREENSIZE[0] / 2) - (gravitywellrect.width / 2)
gravitywellrect.top = (SCREENSIZE[1] / 2) - (gravitywellrect.height / 2)
gravitywell_center = (SCREENSIZE[0] / 2, SCREENSIZE[1] / 2)

fpslimiter = pygame.time.Clock()

screen = pygame.display.set_mode(SCREENSIZE)

playerNumber = None  # basically chosen by server, can be 1 or 2

while True:
    try:
        msg, addr = sock.recvfrom(mplib.maximumsize)
    except BlockingIOError:
        msg = b''
    if msg == b'':
        pass  # no multiplayer updates
    elif state == STATE_HELLOSENT:
        if msg[0 : len(mplib.serverhello)] == mplib.serverhello:
            mptoken = msg[len(mplib.serverhello) : ]
            sock.sendto(mptoken, SERVER)
            state = STATE_TOKENSENT
            statusmessage = 'Completing server handshake...'
        else:
            statusmessage = 'Server protocol error, please restart the game.'

    elif state == STATE_TOKENSENT:
        if msg == mplib.urplayerone:
            statusmessage = 'Server connection established. Waiting for another player to join this server...'
            playerNumber = 1
        elif msg == mplib.playerfound:
            state = STATE_MATCHED
            reply = struct.pack(mplib.configstruct,
                GAMEVERSION,
                Player.P1_START_X,
                Player.P1_START_Y,
                int(round(Player.P1_START_XSPEED * 100)),
                int(round(Player.P1_START_YSPEED * 100)),
                Player.P2_START_X,
                Player.P2_START_Y,
                int(round(Player.P2_START_XSPEED * 100)),
                int(round(Player.P2_START_YSPEED * 100)),
                Player.BATTERY_CAPACITY,
                Player.THRUST,
                int(round(math.log(gravitywell_mass, 1.1))),
            )
            sock.sendto(reply, SERVER)
            sock.sendto(reply, sock.getsockname())  # also send it to ourselves
        elif msg == mplib.urplayertwo:
            statusmessage = 'Server found a match! Waiting for the other player to send game data...'
            playerNumber = 2
            state = STATE_MATCHED
        else:
            statusmessage = 'Server protocol error, please restart the game.'
            print('Got from server:', msg)

    elif state == STATE_MATCHED:
        gameversion, p1startx, p1starty, p1startxspeed, p1startyspeed, p2startx, p2starty, p2startxspeed, p2startyspeed, batcap, enginethrust, gwmass \
            = struct.unpack(mplib.configstruct, msg)

        if GAMEVERSION != gameversion:
            print('Incompatible game version', gameversion)
            stopgame(reason='Incompatible version', exitstatus=2)

        Player.BATTERY_CAPACITY = batcap
        Player.THRUST = enginethrust
        gravitywell_mass = pow(1.1, gwmass)
        players[0 if playerNumber == 1 else 1].pos = {
            'x': p1startx,
            'y': p1starty,
        }
        players[0 if playerNumber == 1 else 1].speed = {
            'x': p1startxspeed / 100,
            'y': p1startyspeed / 100,
        }
        players[1 if playerNumber == 1 else 0].pos = {
            'x': p2startx,
            'y': p2starty,
        }
        players[1 if playerNumber == 1 else 0].speed = {
            'x': p2startxspeed / 100,
            'y': p2startyspeed / 100,
        }
        state = STATE_PLAYERING

    elif state == STATE_PLAYERING:
        if msg.startswith(mplib.playerquits):
            statusmessage = 'Received: ' + str(msg[len(mplib.playerquits) : ], 'ASCII')
        else:
            x, y, xspeed, yspeed, angle = struct.unpack(mplib.updatestruct, msg)
            players[1].angle = angle * 1.5
            players[1].pos = {
                'x': x,
                'y': y,
            }
            players[1].speed = {
                'x': xspeed / 100,
                'y': yspeed / 100,
            }


    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            stopgame(reason='player closed the game window') 
    keystates = pygame.key.get_pressed()

    if keystates[pygame.K_ESCAPE]:
        stopgame(reason='player pressed escape key and successfully fled the arena')

    screen.fill((0, 0, 0))

    if state == STATE_PLAYERING:
        players[0].rotate(keystates[pygame.K_LEFT] - keystates[pygame.K_RIGHT])

        if keystates[pygame.K_UP]:
            players[0].thrust()

        for player in players:
            player.draw(screen)
            player.gravity(gravitywell_center, gravitywell_mass)
            player.update()

        msg = struct.pack(mplib.updatestruct,
            int(round(min(SCREENSIZE[0] + 1000, max(-1000, players[0].pos['x'])))),
            int(round(min(SCREENSIZE[1] + 1000, max(-1000, players[0].pos['y'])))),
            int(round(min(1000, max(-1000, players[0].speed['x'] * 100)))),
            int(round(min(1000, max(-1000, players[0].speed['y'] * 100)))),
            int(round(players[0].angle / 1.5)),
        )
        sock.sendto(msg, SERVER)

    screen.blit(gravitywell, gravitywellrect)

    if len(statusmessage) > 0:
        msgpart = statusmessage[0 : int(time.time() * len(statusmessage)) % (len(statusmessage) * 2)]
        surface = font.render(msgpart, True, (0, 30, 174))
        screen.blit(surface, (10, 50))

    pygame.display.flip()
    fpslimiter.tick(FPS)

