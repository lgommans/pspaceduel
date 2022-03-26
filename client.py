#!/usr/bin/env python3

import sys, math, socket, time, struct, threading
import pygame
import mplib
from luclib import *

class Bullet(pygame.sprite.Sprite):
    DAMAGE = 0.1
    MASS = 0.5
    SPEED = 4
    SIZE = 2
    MAX_OUT_OF_SCREEN = 1  # times the screen width/height
    COLOR = (240, 120, 0)

    def __init__(self, playerobj, virtual=False):
        pygame.sprite.Sprite.__init__(self)

        x = playerobj.pos.x + lengthdir_x(playerobj.rect.width + playerobj.rect.height, playerobj.angle)
        y = playerobj.pos.y + lengthdir_y(playerobj.rect.width + playerobj.rect.height, playerobj.angle)
        self.pos = pygame.math.Vector2(x, y)
        self.speed = pygame.math.Vector2(playerobj.speed)
        self.speed.x += lengthdir_x(Bullet.SPEED, playerobj.angle)
        self.speed.y += lengthdir_y(Bullet.SPEED, playerobj.angle)
        self.belongsTo = playerobj.n
        self.radius = Bullet.SIZE
        self.image = pygame.surface.Surface((Bullet.SIZE * 2, Bullet.SIZE * 2), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=self.pos)
        self.virtual = virtual
        if not virtual:
            pygame.draw.circle(self.image, Bullet.COLOR, (Bullet.SIZE, Bullet.SIZE), Bullet.SIZE)

    def advance(self):
        # Returns whether it should be removed (out of screen, fell into gravity well; no health-bearing-object collisions)

        accelx, accely, separation = gravity(self.pos, gravitywell_center, Bullet.MASS, gravitywell_mass)
        self.speed.x -= accelx
        self.speed.y -= accely
        self.pos.x += self.speed.x
        self.pos.y += self.speed.y
        self.rect.center = (roundi(self.pos.x), roundi(self.pos.y))

        if players[0].n == self.belongsTo and separation < gravitywellrect.width / 2:  # assumed to be spherical
            return True

        if self.pos.x < -SCREENSIZE[0] * Bullet.MAX_OUT_OF_SCREEN or self.pos.x > SCREENSIZE[0] + (SCREENSIZE[0] * Bullet.MAX_OUT_OF_SCREEN) \
        or self.pos.y < -SCREENSIZE[1] * Bullet.MAX_OUT_OF_SCREEN or self.pos.y > SCREENSIZE[1] + (SCREENSIZE[1] * Bullet.MAX_OUT_OF_SCREEN):
            return True

        return False


class Player:
    SCALE = (0.25, 0.25)
    INDICATORHEIGHT = 0.18  # as a fraction of the player height after scaling
    INDICATORDISTANCE = 0.6  # as a fraction of the player height after scaling
    ROTATIONAL_SPEED = 4
    ROTATIONAL_SPEED_FINE = 0.8
    MASS = 100  # kg
    P1_START_X = 300
    P1_START_Y = 300
    P1_START_XSPEED = 1
    P1_START_YSPEED = -1
    P2_START_X = 900
    P2_START_Y = 700
    P2_START_XSPEED = -1
    P2_START_YSPEED = 1
    BATTERY_CAPACITY = 100  # kJ -- Ingenuity (Mars rover) has 130 kJ for comparison
    # A real ion engine delivers more like 1 Newton on 5 kW, but we're also orbiting a star in seconds and other unrealistic things
    THRUST = 600  # Newtons
    THRUST_PER_kJ = 1200  # newtons you get out of each kJ
    RELOADTIME = 0.75  # seconds
    MINRELOADSTATE = -0.75  # times the reloadtime

    def __init__(self, n):
        img = pygame.image.load(f'res/player{n}.png')
        rect = img.get_rect()

        self.n = n
        self.seqno = 0
        self.img = pygame.transform.scale(img, (roundi(rect.width * Player.SCALE[0]), roundi(rect.height * Player.SCALE[1])))
        self.rect = self.img.get_rect()
        self.spr = pygame.sprite.Sprite()
        self.spr.image = self.img
        self.spr.rect = self.rect
        self.spr.mask = pygame.mask.from_surface(self.img)

        self.angle = 0  # 0-360
        self.health = 1  # 0-1
        self.pos = None  # initialized when round starts
        self.speed = None
        self.batterylevel = Player.BATTERY_CAPACITY
        self.reloadstate = 0

    def thrust(self):
        if self.batterylevel > Player.THRUST / Player.THRUST_PER_kJ:
            self.speed.x += lengthdir_x(Player.THRUST * FRAMETIME / Player.MASS, self.angle)
            self.speed.y += lengthdir_y(Player.THRUST * FRAMETIME / Player.MASS, self.angle)
            self.batterylevel -= Player.THRUST / Player.THRUST_PER_kJ

    def draw(self, screen):
        blitRotateCenter(screen, self.img, (roundi(self.spr.rect.left), roundi(self.spr.rect.top)), self.angle)

    def rotate(self, direction, fine=False):  # direction is 1 or -1
        self.angle += direction * (Player.ROTATIONAL_SPEED if not fine else Player.ROTATIONAL_SPEED_FINE)
        self.angle %= 360
        rotated_image = pygame.transform.rotate(self.img, self.angle)
        self.spr.mask = pygame.mask.from_surface(rotated_image)

    def update(self):
        # It is assumed that the 'towards' object is at a fixed position (a gravity well). It will not be updated according to forces felt

        if self.reloadstate > FPS * Player.RELOADTIME * Player.MINRELOADSTATE:
            self.reloadstate -= 1

        accelx, accely, separation = gravity(self.pos, gravitywell_center, Player.MASS, gravitywell_mass)
        self.speed.x -= accelx
        self.speed.y -= accely
        self.pos.x += self.speed.x / GRAVITATIONSTEPS
        self.pos.y += self.speed.y / GRAVITATIONSTEPS

        self.spr.rect.left = roundi(self.pos.x)
        self.spr.rect.top = roundi(self.pos.y)

        if players[0].n == self.n and separation < gravitywellrect.width / 2:  # assumed to be spherical
            playerDied(other=False)
            return

        if pygame.sprite.collide_mask(players[0].spr, players[1].spr) is not None:
            # If you run into each other, you both die. Should have run, you fools
            playerDied(other=False)
            playerDied(other=True)

        radiative_power = gravitywell_radiation_1km / (separation * separation) * 1000
        self.batterylevel = min(Player.BATTERY_CAPACITY, self.batterylevel + radiative_power)


def gravity(obj1pos, obj2pos, obj1mass, obj2mass):
    separation_x = obj1pos.x - obj2pos.x
    separation_y = obj1pos.y - obj2pos.y
    separation = math.sqrt(separation_x * separation_x + separation_y * separation_y)
    grav_accel = obj1mass * obj2mass / (separation * separation) * (FRAMETIME * GRAVITYCONSTANT)
    dir_x = separation_x / separation
    dir_y = separation_y / separation
    return grav_accel / obj1mass * dir_x, grav_accel / obj1mass * dir_y, separation


def distance(obj1, obj2):
    sep_x = players[0].pos.x - players[1].pos.x
    sep_y = players[0].pos.y - players[1].pos.y
    return ((sep_x * sep_x) + (sep_y * sep_y))


def playerDied(other=False):
    # other: did the other player die or did we die?
    global statusmessage, state

    if state == STATE_DEAD:  # if someone already died and we get another death event...
        statusmessage = 'Tied'
    else:
        state = STATE_DEAD
        if other:
            statusmessage = 'You won'
        else:
            statusmessage = 'You died'
            if not SINGLEPLAYER:
                sock.sendto(b'\x01', SERVER)


def roundi(n):  # because pygame wants an int and round() returns a float for some reason but int() drops the fractional part... pain in the bum, here's a shortcut...
    return int(round(n))


def blitRotateCenter(surf, image, pos, angle):
    # this function is CC-BY-SA 4.0 by Rabbid76 from https://stackoverflow.com/a/54714144
    rotated_image = pygame.transform.rotate(image, angle)
    new_rect = rotated_image.get_rect(center=image.get_rect(topleft = pos).center)
    surf.blit(rotated_image, new_rect)


def stopgame(reason, exitstatus=0):
    if not SINGLEPLAYER:
        sock.sendto(mplib.playerquits + reason.encode('ASCII'), SERVER)
    sys.exit(exitstatus)


def sendto(sock, msg, server):
    sock.sendto(msg, server)


GAMEVERSION = 1
GRAVITYCONSTANT = 6.6742e-11
GRAVITATIONSTEPS = 1
SCREENSIZE = (1440, 900)
FPS = 60
FRAMETIME = 1 / FPS
FTGC = FRAMETIME * GRAVITYCONSTANT
PREDICTIONDISTANCE = FPS * 2
SERVER = ('127.0.0.1', 9473)
SINGLEPLAYER = True

STATE_HELLOSENT = 1
STATE_TOKENSENT = 2
STATE_MATCHED   = 3
STATE_PLAYERING = 4
STATE_DEAD      = 5

if not SINGLEPLAYER:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(0)
    sock.sendto(mplib.clienthello, SERVER)
    mptoken = None
    state = STATE_HELLOSENT
    statusmessage = 'Waiting for server initial response...'
else:
    statusmessage = ''

# don't just pygame.init() because it will hang and not quit when you do pygame.quit();sys.exit();. Stackoverflow suggests in 2013 this was a Wheezy bug, but it works on a
# newer-than-Wheezy system, and then does not work on an even newer system than that, so... initializing only what we need is literally 20 times faster (0.02 instead of 0.4 s) anyway!
pygame.display.init()
pygame.font.init()
font_statusMsg = pygame.font.SysFont(None, 48)

bullets = pygame.sprite.Group()
players = [
    Player(1),
    Player(2),
]

gravitywell = pygame.image.load(f'res/sun.png')
gravitywell_mass = 1e15
gravitywellrect = gravitywell.get_rect()
gravitywellrect.left = roundi((SCREENSIZE[0] / 2) - (gravitywellrect.width / 2))
gravitywellrect.top = roundi((SCREENSIZE[1] / 2) - (gravitywellrect.height / 2))
gravitywell_center = pygame.math.Vector2(SCREENSIZE[0] / 2, SCREENSIZE[1] / 2)
gravitywell_radiation_1km = 10  # How many kW the spacecraft practically get at 1 km (pixel) distance (considering solar panel size and effiency)

fpslimiter = pygame.time.Clock()

screen = pygame.display.set_mode(SCREENSIZE)

players[0].seqno += 1

if SINGLEPLAYER:
    players[0].pos = pygame.math.Vector2(Player.P1_START_X, Player.P1_START_Y)
    players[0].speed = pygame.math.Vector2(Player.P1_START_XSPEED, Player.P1_START_YSPEED)
    players[1].pos = pygame.math.Vector2(Player.P2_START_X, Player.P2_START_Y)
    players[1].speed = pygame.math.Vector2(Player.P2_START_XSPEED, Player.P2_START_YSPEED)
    state = STATE_PLAYERING

while True:
    if not SINGLEPLAYER:
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
                players[0].n = 1
                players[1].n = 2
            elif msg == mplib.playerfound:
                state = STATE_MATCHED
                reply = struct.pack(mplib.configstruct,
                    GAMEVERSION,
                    Player.P1_START_X,
                    Player.P1_START_Y,
                    roundi(Player.P1_START_XSPEED * 100),
                    roundi(Player.P1_START_YSPEED * 100),
                    Player.P2_START_X,
                    Player.P2_START_Y,
                    roundi(Player.P2_START_XSPEED * 100),
                    roundi(Player.P2_START_YSPEED * 100),
                    Player.BATTERY_CAPACITY,
                    Player.THRUST,
                    Player.THRUST_PER_kJ,
                    roundi(math.log(gravitywell_mass, 1.1)),
                    roundi(gravitywell_radiation_1km),
                    roundi(Bullet.DAMAGE * 255),
                )
                sock.sendto(reply, SERVER)
                sock.sendto(reply, ('127.0.0.1', sock.getsockname()[1]))  # also send it to ourselves
            elif msg == mplib.urplayertwo:
                statusmessage = 'Server found a match! Waiting for the other player to send game data...'
                players[0].n = 2
                players[1].n = 1
                state = STATE_MATCHED
            else:
                statusmessage = 'Server protocol error, please restart the game.'
                print('Got from server:', msg)

        elif state == STATE_MATCHED:
            gameversion, p1startx, p1starty, p1startxspeed, p1startyspeed, p2startx, p2starty, p2startxspeed, p2startyspeed, batcap, enginethrust, thrustperkj, gwmass, gwrad, bulletdmg \
                = struct.unpack(mplib.configstruct, msg)

            if GAMEVERSION != gameversion:
                print('Incompatible game version', gameversion)
                stopgame(reason='Incompatible version', exitstatus=2)

            Player.BATTERY_CAPACITY = batcap
            Player.THRUST = enginethrust
            Player.THRUST_PER_kJ = thrustperkj
            Bullet.DAMAGE = bulletdmg / 255
            gravitywell_mass = pow(1.1, gwmass)
            gravitywell_radiation_1km = gwrad
            players[players[0].n - 1].pos = pygame.math.Vector2(p1startx, p1starty)
            players[players[0].n - 1].speed = pygame.math.Vector2(p1startxspeed / 100, p1startyspeed / 100)
            players[players[1].n - 1].pos = pygame.math.Vector2(p2startx, p2starty)
            players[players[1].n - 1].speed = pygame.math.Vector2(p2startxspeed / 100, p2startyspeed / 100)
            state = STATE_PLAYERING
            statusmessage = ''

        elif state == STATE_PLAYERING:
            if msg.startswith(mplib.playerquits):
                print('other player quit for reason:', msg)
                statusmessage = 'Received: ' + str(msg[len(mplib.playerquits) : ], 'ASCII')
            elif msg[0] == 0:
                seqno, x, y, xspeed, yspeed, angle, batlvl, health = struct.unpack(mplib.updatestruct, msg[1 : ])
                if seqno <= players[1].seqno:
                    print('Ignored seqno', seqno, ' because the last seqno for this player was', players[1].seqno)
                else:
                    if seqno - 1 != players[1].seqno:
                        print('Info: packet loss. Received seqno', seqno, ' whereas the last seqno for this player was', players[1].seqno)
                    players[1].seqno = seqno
                    players[1].angle = angle * 1.5
                    players[1].pos = pygame.math.Vector2(x, y)
                    players[1].speed = pygame.math.Vector2(xspeed / 100, yspeed / 100)
                    players[1].batterylevel = batlvl / 255 * Player.BATTERY_CAPACITY
                    players[1].health = health / 255
            elif msg[0] == 1:
                playerDied(other=True)


    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            stopgame(reason='player closed the game window') 
    keystates = pygame.key.get_pressed()

    if keystates[pygame.K_ESCAPE]:
        stopgame(reason='player pressed escape key and successfully fled the arena')

    screen.fill((0, 0, 0))

    if state == STATE_PLAYERING:
        players[0].rotate(keystates[pygame.K_LEFT] - keystates[pygame.K_RIGHT], keystates[pygame.K_LSHIFT] or keystates[pygame.K_RSHIFT])

        if keystates[pygame.K_SPACE]:
            if players[0].reloadstate <= 0:
                players[0].reloadstate += FPS * Player.RELOADTIME
                bull = Bullet(players[0])
                bullets.add(bull)

        if keystates[pygame.K_UP]:
            players[0].thrust()

        removebullets = []
        for bullet in bullets:
            died = bullet.advance()
            if died:
                removebullets.append(bullet)
        for bullet in removebullets:
            if bullet.belongsTo == players[0].n:
                # TODO sync bullet stuff to multiplayer
                bullets.remove(bullet)
        for player in players:
            removebullets = pygame.sprite.spritecollide(player.spr, bullets, False, pygame.sprite.collide_circle)
            for bullet in removebullets:
                if bullet.belongsTo == players[0].n:
                    # TODO sync bullet stuff to multiplayer
                    player.health -= Bullet.DAMAGE
                    # TODO playerDied(...)
                    bullets.remove(bullet)

        bullets.draw(screen)

        for player in players:
            player.update()
            player.draw(screen)

            w, h = player.rect.width, player.rect.height
            x, y = player.pos.x + (w / 2), player.pos.y + (h / 2)
            idis = h * Player.INDICATORDISTANCE

            # Draw battery level indicators
            bl = player.batterylevel / Player.BATTERY_CAPACITY
            poweryellow = (255, 200, 0)
            indicatorcolor = poweryellow if player.batterylevel > Player.THRUST / Player.THRUST_PER_kJ else (255, 0, 0)
            # outer rectangle
            pygame.draw.rect(screen, indicatorcolor, (roundi(x - w - 1), roundi(player.pos.y + h + idis + 1), roundi((w * 2 + 2)), roundi(h * Player.INDICATORHEIGHT + 2)))
            # inner black area (same area as above but -1px on each side)
            pygame.draw.rect(screen, (  0,   0,  0), (roundi(x - w - 0), roundi(player.pos.y + h + idis + 2), roundi((w * 2 + 0)), roundi(h * Player.INDICATORHEIGHT + 0)))
            # battery level (drawn over the black area)
            pygame.draw.rect(screen, poweryellow   , (roundi(x - w - 0), roundi(player.pos.y + h + idis + 2), roundi((w * 2 + 0) * bl), roundi(h * Player.INDICATORHEIGHT + 0)))

            # Draw health indicators
            healthgreen = (10, 230, 10)
            indicatorcolor = healthgreen if player.health > Bullet.DAMAGE else (255, 100, 0)
            # outer rectangle
            pygame.draw.rect(screen, indicatorcolor, (roundi(x - w - 1), roundi(player.pos.y - idis - 2), roundi((w * 2 + 2)),                 roundi(h * Player.INDICATORHEIGHT + 2)))
            # inner black area (same area as above but -1px on each side)
            pygame.draw.rect(screen, (  0,   0,  0), (roundi(x - w - 0), roundi(player.pos.y - idis - 1), roundi((w * 2 + 0)),                 roundi(h * Player.INDICATORHEIGHT + 0)))
            # health level (drawn over the black area)
            pygame.draw.rect(screen, healthgreen   , (roundi(x - w - 0), roundi(player.pos.y - idis - 1), roundi((w * 2 + 0) * player.health), roundi(h * Player.INDICATORHEIGHT + 0)))

        b = Bullet(players[0], virtual=True)
        for i in range(PREDICTIONDISTANCE):
            oldpos = pygame.math.Vector2(b.pos)
            died = b.advance()
            if died:
                break
            pygame.draw.line(screen, (80, 0, 0), oldpos, b.pos)

        if not SINGLEPLAYER:
            msg = b'\x00' + struct.pack(mplib.updatestruct,
                players[0].seqno,
                roundi(min(SCREENSIZE[0] + 1000, max(-1000, players[0].pos.x))),
                roundi(min(SCREENSIZE[1] + 1000, max(-1000, players[0].pos.y))),
                roundi(min(1000, max(-1000, players[0].speed.x * 100))),
                roundi(min(1000, max(-1000, players[0].speed.y * 100))),
                roundi(players[0].angle / 1.5),
                roundi(players[0].batterylevel / Player.BATTERY_CAPACITY * 255),
                roundi(players[0].health * 255),
            )
            players[0].seqno += 1
            # TODO instead of creating a new thread every time, put the msg in some variable and unblock/notify the thread to send it
            threading.Thread(target=sendto, args=(sock, msg, SERVER)).start()

    screen.blit(gravitywell, gravitywellrect)

    if len(statusmessage) > 0:
        msgpart = statusmessage[0 : int(time.time() * len(statusmessage)) % (len(statusmessage) * 2)]
        surface = font_statusMsg.render(msgpart, True, (0, 30, 174))
        screen.blit(surface, (10, 50))

    pygame.display.flip()
    frametime = fpslimiter.tick(FPS)
    if frametime * 0.9 > FRAMETIME * 1000:  # 10% margin because it will sleep longer sometimes to keep the fps *below* the target amount
        print('frametime was', frametime)

