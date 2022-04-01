#!/usr/bin/env python3

import sys, math, socket, time, threading, random
from inspect import currentframe  # temporarily for timeme()
import pygame
import mplib
from settings import Setting, settings
from luclib import *

class Spark:
    LIFESPAN = (4, 10)  # frames: (min, max)
    MOVEMENT = (1, 2)  # pixels it randomly moves per frame in each direction: (min, max)
    ROTATION = (2, 90)  # range of the degrees it rotates per frame: (min, max). The direction (positive or negative rotation) is a 50/50 chance
    IMAGE = pygame.image.load('res/venting.png')

    def __init__(self, pos):
        self.pos = pygame.math.Vector2(pos)
        self.lifespan = random.randint(*Spark.LIFESPAN)
        self.angle = random.randint(0, 360)
        self.rotation = random.randint(*Spark.ROTATION) * (-1 if random.randint(1, 2) == 1 else 1)

    def updateAndDraw(self, screen):
        # returns whether it needs to be destroyed

        self.lifespan -= 1
        if self.lifespan <= 0:
            return True

        self.pos.x += random.randint(*Spark.MOVEMENT) * (-1 if random.randint(1, 2) == 1 else 1)
        self.pos.y += random.randint(*Spark.MOVEMENT) * (-1 if random.randint(1, 2) == 1 else 1)
        self.angle += self.rotation

        rotated_image = pygame.transform.rotate(Spark.IMAGE, self.angle)
        screen.blit(rotated_image, (roundi(self.pos.x), roundi(self.pos.y)))


class Bullet(pygame.sprite.Sprite):
    COLOR = (240, 120, 0)
    # multiplied with the screen width/height -- set relatively low because players might otherwise wonder why bullets are coming out of nowhere when the shot was just below escape velocity
    MAX_OUT_OF_SCREEN = 0.25

    def __init__(self, playerobj, virtual=False):
        pygame.sprite.Sprite.__init__(self)

        x = playerobj.spr.rect.center[0] + lengthdir_x(playerobj.spr.rect.height, playerobj.angle)
        y = playerobj.spr.rect.center[1] + lengthdir_y(playerobj.spr.rect.height, playerobj.angle)
        self.pos = pygame.math.Vector2(x, y)
        if settings['Bullet.relspeed'].val:
            self.speed = pygame.math.Vector2(playerobj.speed)
        else:
            self.speed = pygame.math.Vector2(0, 0)
        self.speed.x += lengthdir_x(settings['Bullet.speed'].val, playerobj.angle)
        self.speed.y += lengthdir_y(settings['Bullet.speed'].val, playerobj.angle)
        self.belongsTo = playerobj.n
        self.radius = settings['Bullet.size'].val
        self.virtual = virtual
        if not virtual:
            bulletsize = settings['Bullet.size'].val
            self.image = pygame.surface.Surface((bulletsize * 2, bulletsize * 2), pygame.SRCALPHA)
            self.rect = self.image.get_rect(center=self.pos)
            pygame.draw.circle(self.image, Bullet.COLOR, (bulletsize, bulletsize), bulletsize)
            self.image = self.image.convert()

    def advance(self):
        # Returns whether it should be removed (out of screen, fell into gravity well; no health-bearing-object collisions)

        accelx, accely, separation = gravity(self.pos, gravitywell_center, settings['Bullet.mass'].val, settings['GW.mass'].val)
        self.speed.x -= accelx
        self.speed.y -= accely
        self.pos.x += self.speed.x
        self.pos.y += self.speed.y
        if not self.virtual:
            self.rect.center = (roundi(self.pos.x), roundi(self.pos.y))

        if players[0].n == self.belongsTo and separation < gravitywellrect.width / 2:  # GW assumed to be spherical
            return True

        if self.pos.x < -SCREENSIZE[0] * Bullet.MAX_OUT_OF_SCREEN or self.pos.x > SCREENSIZE[0] + (SCREENSIZE[0] * Bullet.MAX_OUT_OF_SCREEN) \
        or self.pos.y < -SCREENSIZE[1] * Bullet.MAX_OUT_OF_SCREEN or self.pos.y > SCREENSIZE[1] + (SCREENSIZE[1] * Bullet.MAX_OUT_OF_SCREEN):
            return True

        return False


class Player:
    INDICATORHEIGHT = 0.18  # as a fraction of the player height after scaling
    INDICATORDISTANCE = 0.6  # as a fraction of the player height after scaling
    ROTATIONAL_SPEED = 4  # degrees per game step. Left as player preference because I'm fine if they want to rotate faster... just costs more energy then
    ROTATIONAL_SPEED_FINE = 0.8

    def __init__(self, n):
        img = pygame.image.load(f'res/player{n}.png')
        rect = img.get_rect()

        self.n = n
        self.seqno = 0
        self.img = pygame.transform.scale(img, (roundi(rect.width * settings['Player.scale'].val), roundi(rect.height * settings['Player.scale'].val)))
        self.img = self.img.convert_alpha()
        self.spr = pygame.sprite.Sprite()
        self.spr.image = self.img
        self.spr.rect = self.img.get_rect()
        self.spr.mask = pygame.mask.from_surface(self.img)
        self.pos = None
        self.speed = None
        self.reinitialize()

    def reinitialize(self):
        self.angle = 0  # 0-360
        self.health = 1  # 0-1
        self.batterylevel = settings['Player.battSize'].val
        self.reloadstate = 0

    def thrust(self):
        if self.batterylevel > settings['Player.thrust'].val / settings['Player.thrust/kJ'].val:
            self.speed.x += lengthdir_x(settings['Player.thrust'].val * FRAMETIME / settings['Player.mass'].val, self.angle)
            self.speed.y += lengthdir_y(settings['Player.thrust'].val * FRAMETIME / settings['Player.mass'].val, self.angle)
            self.batterylevel -= settings['Player.thrust'].val / settings['Player.thrust/kJ'].val

    def draw(self, screen):
        self.spr.rect.left = roundi(self.pos.x)
        self.spr.rect.top = roundi(self.pos.y)

        blitRotateCenter(screen, self.img, (roundi(self.spr.rect.left), roundi(self.spr.rect.top)), self.angle)

    def rotate(self, direction, fine=False):  # direction is 1 or -1
        if direction == 0:
            return

        rotationamount = direction * (Player.ROTATIONAL_SPEED if not fine else Player.ROTATIONAL_SPEED_FINE)
        if self.batterylevel > abs(rotationamount) / settings['Player.rot/kJ'].val:
            self.batterylevel -= abs(rotationamount) / settings['Player.rot/kJ'].val
            self.angle += rotationamount
            self.angle %= 360
            rotated_image = pygame.transform.rotate(self.img, self.angle)
            self.spr.mask = pygame.mask.from_surface(rotated_image)

    def update(self):  # this function should only be run on the local player, since it calls playerDied which triggers network events
        global gamescore

        if self.health <= 0:
            if SINGLEPLAYER and self == players[1]:
                playerDied(other=True)
            else:
                playerDied(other=False)
            return

        if self.reloadstate > FPS * settings['Player.reload'].val * settings['Player.minreload'].val:
            self.reloadstate -= 1

        # It is assumed that the 'towards' object is at a fixed position (a gravity well). It will not be updated according to forces felt
        accelx, accely, separation = gravity(pygame.math.Vector2(self.spr.rect.center), gravitywell_center, settings['Player.mass'].val, settings['GW.mass'].val)
        self.speed.x -= accelx
        self.speed.y -= accely
        self.pos.x += self.speed.x
        self.pos.y += self.speed.y

        if separation < (gravitywellrect.width / 2) + (self.spr.rect.width / 2):  # GW assumed to be spherical
            playerDied(other=False)
            return

        if self.pos.x < settings['Player.visiblepx'].val - self.spr.rect.width:
            self.pos.x = SCREENSIZE[0] - settings['Player.visiblepx'].val
        elif self.pos.x > SCREENSIZE[0] - settings['Player.visiblepx'].val:
            self.pos.x = settings['Player.visiblepx'].val - self.spr.rect.width
        if self.pos.y < settings['Player.visiblepx'].val - self.spr.rect.height:
            self.pos.y = SCREENSIZE[1] - settings['Player.visiblepx'].val
        elif self.pos.y > SCREENSIZE[1] - settings['Player.visiblepx'].val:
            self.pos.y = settings['Player.visiblepx'].val - self.spr.rect.height

        if pygame.sprite.collide_mask(players[0].spr, players[1].spr) is not None:
            # If you run into each other, you both die. Should have run, you fools
            playerDied(both=True)

        radiative_power = settings['GW.radiation'].val / (separation * separation) * 1000
        self.batterylevel = min(settings['Player.battSize'].val, self.batterylevel + radiative_power)


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


def playerDied(other=False, both=False, sendpacket=True):
    # other: did the other player die or did we die?
    global statusmessage, state, gamescore

    state = STATE_DEAD

    if both:
        gamescore = 1
        statusmessage = 'You tied: 1 point! Your score: ' + str(score + gamescore) + '. Press Enter to restart.'
        if not SINGLEPLAYER and sendpacket:
            sendtoQueued(b'\x01\x01')
    else:
        if other:
            gamescore = 5
            statusmessage = 'You won: 5 points! Your score: ' + str(score + gamescore) + '. Press Enter to restart.'
        else:
            statusmessage = 'You died. Your score: ' + str(score) + '. Press Enter to restart.'
            if not SINGLEPLAYER and sendpacket:
                sendtoQueued(b'\x01')


def roundi(n):  # because pygame wants an int and round() returns a float for some reason but int() drops the fractional part... pain in the bum, here's a shortcut...
    return int(round(n))


def blitRotateCenter(surf, image, pos, angle):
    # this function is CC-BY-SA 4.0 by Rabbid76 from https://stackoverflow.com/a/54714144
    rotated_image = pygame.transform.rotate(image, angle)
    new_rect = rotated_image.get_rect(center=image.get_rect(topleft = pos).center)
    surf.blit(rotated_image, new_rect)


def stopgame(reason, exitstatus=0):
    global stopSendtoThread

    if not SINGLEPLAYER:
        stopSendtoThread = True
        msgQueueEvent.set()
        sock.sendto(mplib.playerquits + reason.encode('ASCII'), SERVER)

    sys.exit(exitstatus)


def initSinglePlayer():
    players[0].pos = pygame.math.Vector2(settings['Player1.x'].val, settings['Player1.y'].val)
    players[0].speed = pygame.math.Vector2(settings['Player1.xspeed'].val, settings['Player1.yspeed'].val)
    players[0].draw(screen)  # updates the sprite position to avoid a collision
    players[1].pos = pygame.math.Vector2(settings['Player2.x'].val, settings['Player2.y'].val)
    players[1].speed = pygame.math.Vector2(settings['Player2.xspeed'].val, settings['Player2.yspeed'].val)
    globalReinitialize()


def globalReinitialize():
    global sparks, bullets, remotebullets, gamescore

    sparks = []
    bullets = pygame.sprite.Group()
    remotebullets = []
    players[0].reinitialize()
    players[1].reinitialize()
    gamescore = 0


def sendto():
    while True:
        if len(msgQueue) == 0:
            # Doing this thread blocking/unblocking is ~13× faster than starting a new thread for every packet
            msgQueueEvent.clear()
            msgQueueEvent.wait()

        if stopSendtoThread:
            break

        try:
            msg = msgQueue.pop(0)
            sock.sendto(msg, SERVER)
        except IndexError:
            # We somehow managed to try and pop an empty list
            print('moin? We were asked to send something but there is nothing in the queue? Going back to sleep...')


def sendtoQueued(msg):
    msgQueue.append(msg)
    msgQueueEvent.set()


starttime = time.time()
def timeme(out=True, th=0):  # params: show output; threshold above which it should be shown
    global starttime
    now = time.time()
    cf = currentframe()
    ln = cf.f_back.f_lineno  # line number of the parent stack frame
    if out:
        td = (now - starttime) * 1000000
        if th < td:
            print(ln, td, 'µs')
    starttime = now


GAMEVERSION = 1
GRAVITYCONSTANT = 6.6742e-11
SCREENSIZE = (1440, 900)
FPS = 60
FRAMETIME = 1 / FPS
FTGC = FRAMETIME * GRAVITYCONSTANT
PREDICTIONDISTANCE = FPS * 2
PINGEVERY = 4  # measure ping time randomly every PINGEVERY/2--PINGEVERY*2 seconds
SIMPLEGRAPHICS = True
SERVER = ('lucgommans.nl', 9473)
SINGLEPLAYER = False

STATE_INITIAL   = 0
STATE_HELLOSENT = 1
STATE_TOKENSENT = 2
STATE_MATCHED   = 3
STATE_PLAYERING = 4
STATE_DEAD      = 5

score = 0

if not SINGLEPLAYER:
    state = STATE_INITIAL
else:
    state = STATE_PLAYERING
    statusmessage = ''

# don't just pygame.init() because it will hang and not quit when you do pygame.quit();sys.exit();. Stackoverflow suggests in 2013 this was a Wheezy bug, but it works on a
# newer-than-Wheezy system, and then does not work on an even newer system than that, so... initializing only what we need is also literally 20 times faster (0.02 instead of 0.4 s)!
pygame.display.init()
pygame.font.init()
font_statusMsg = pygame.font.SysFont(None, 48)
fpslimiter = pygame.time.Clock()
screen = pygame.display.set_mode(SCREENSIZE)

# if dns lookup is needed, do this now (works also if you enter an IP, gethostbyname will just return it literally)
# else sock.sendto() will do dns lookup for every call and, depending on the setup, that might hit the network for sending each individual update packet
SERVER = (socket.gethostbyname(SERVER[0]), SERVER[1])

sparks = []
bullets = pygame.sprite.Group()
remotebullets = []
players = [
    Player(1),
    Player(2),
]
hitsdealt = 0

gravitywell = pygame.image.load(f'res/sun.png')
gravitywell = gravitywell.convert_alpha()
gravitywellrect = gravitywell.get_rect()
gravitywellrect.left = roundi((SCREENSIZE[0] / 2) - (gravitywellrect.width / 2))
gravitywellrect.top = roundi((SCREENSIZE[1] / 2) - (gravitywellrect.height / 2))
gravitywell_center = pygame.math.Vector2(SCREENSIZE[0] / 2, SCREENSIZE[1] / 2)
gravitywell_center_int = (roundi(gravitywell_center.x), roundi(gravitywell_center.y))  # because pygame doesn't want a normal Vector2 as position to draw a circle on...

if SINGLEPLAYER:
    initSinglePlayer()
else:
    sock = None
    stopSendtoThread = False
    msgQueue = []  # apparently a regular list is thread-safe in python in 2022
    msgQueueEvent = threading.Event()
    threading.Thread(target=sendto).start()

while True:
    if not SINGLEPLAYER:
        if state == STATE_INITIAL:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setblocking(0)
            sendtoQueued(mplib.clienthello)
            mptoken = None
            state = STATE_HELLOSENT
            statusmessage = 'Waiting for server initial response...'

        for _ in range(15):  # process up to N packets per frame (send rate is 1.x per frame)
            try:
                msg, addr = sock.recvfrom(mplib.maximumsize)
            except BlockingIOError:
                msg = b''
            if msg == b'':
                break  # no multiplayer updates
            elif state == STATE_HELLOSENT:
                if msg[0 : len(mplib.serverhello)] != mplib.serverhello:
                    statusmessage = 'Server protocol error, please restart the game.'
                else:
                    mptoken = msg[len(mplib.serverhello) : ]
                    sendtoQueued(mptoken)
                    state = STATE_TOKENSENT
                    statusmessage = 'Completing server handshake...'

                    globalReinitialize()

                    pingSentAt = None
                    nextPingAt = random.randint(FPS * 3, FPS * 4)  # seqno
                    players[0].seqno += 1


            elif state == STATE_TOKENSENT:
                if msg == mplib.urplayerone:
                    statusmessage = 'Server connection established. Waiting for another player to join this server...'
                    players[0].n = 1
                    players[1].n = 2
                elif msg == mplib.playerfound:
                    state = STATE_MATCHED
                    reply = Setting.serializeSettings(settings)
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
                Setting.updateSettings(settings, msg)

                players[players[0].n - 1].pos = pygame.math.Vector2(settings['Player1.x'].val, settings['Player1.y'].val)
                players[players[0].n - 1].speed = pygame.math.Vector2(settings['Player1.xspeed'].val, settings['Player1.yspeed'].val)
                players[players[1].n - 1].pos = pygame.math.Vector2(settings['Player2.x'].val, settings['Player2.y'].val)
                players[players[1].n - 1].speed = pygame.math.Vector2(settings['Player2.xspeed'].val, settings['Player2.yspeed'].val)
                players[0].draw(screen)  # updates the sprite, which also does collision detection, to prevent collision on frame 0
                state = STATE_PLAYERING
                statusmessage = ''

            elif state == STATE_PLAYERING or state == STATE_DEAD:
                if msg.startswith(mplib.playerquits):
                    print('other player sent:', msg)
                    reason = msg[len(mplib.playerquits) : ]
                    if reason == mplib.restartpl0x:
                        statusmessage += ' The other player restarted!'
                    else:
                        if state == STATE_PLAYERING:
                            statusmessage = 'You win! The other player ' + str(reason, 'ASCII')
                        else:
                            statusmessage = 'The other player ' + str(reason, 'ASCII') + '. Your score was: ' + str(score)
                elif msg[0] == 0:
                    seqno, x, y, xspeed, yspeed, angle, batlvl, health, hitsfromtheirbullets = mplib.updatestruct.unpack(msg[1 : 1 + mplib.updatestruct.size])
                    if seqno <= players[1].seqno:
                        print('Ignored seqno', seqno, ' because the last seqno for this player was', players[1].seqno)
                    else:
                        if seqno - 1 != players[1].seqno:
                            print('Info: jitter or loss. Received seqno', seqno, ' whereas the last seqno for this player was', players[1].seqno)
                        players[1].seqno = seqno
                        players[1].angle = angle * 1.5
                        players[1].pos = pygame.math.Vector2(x, y)
                        players[1].speed = pygame.math.Vector2(xspeed / 100, yspeed / 100)
                        players[1].batterylevel = batlvl / 255 * settings['Player.battSize'].val
                        players[1].health = health / 255
                        players[0].health = max(0, players[0].health - (settings['Bullet.damage'].val * hitsfromtheirbullets))
                        msg = msg[1 + mplib.updatestruct.size : ]
                        remotebullets = []
                        while len(msg) > 0:
                            x, y = mplib.bulletstruct.unpack(msg[ : mplib.bulletstruct.size])
                            remotebullets.append((x, y))
                            msg = msg[mplib.bulletstruct.size : ]

                elif msg[0] == 1:
                    if len(msg) > 1 and msg[1] == 1:
                        playerDied(both=True, sendpacket=False)
                    else:
                        playerDied(other=True)

                elif msg[0] == 2:
                    sendtoQueued(b'\x03')

                elif msg[0] == 3:
                    if pingSentAt is not None:
                        ping = (time.time() - pingSentAt) * 1000  # ms
                        print('Ping time:', round(ping), 'ms')
                        pingSentAt = None


    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            stopgame(reason='fled the arena')
    keystates = pygame.key.get_pressed()

    if keystates[pygame.K_ESCAPE]:
        stopgame(reason='fled the arena')

    screen.fill((0, 0, 0))

    if state == STATE_PLAYERING:
        players[0].rotate(keystates[pygame.K_LEFT] - keystates[pygame.K_RIGHT], keystates[pygame.K_LSHIFT] or keystates[pygame.K_RSHIFT])

        if keystates[pygame.K_SPACE]:
            if players[0].reloadstate <= 0 and players[0].batterylevel > settings['Player.kJ/shot'].val:
                players[0].reloadstate += FPS * settings['Player.reload'].val
                players[0].batterylevel -= settings['Player.kJ/shot'].val
                bull = Bullet(players[0])
                bullets.add(bull)

        if keystates[pygame.K_UP]:
            players[0].thrust()

        removebullets = []
        for bullet in bullets:
            if bullet.belongsTo == players[0].n:
                died = bullet.advance()
                if died:
                    removebullets.append(bullet)
        for bullet in removebullets:
            if bullet.belongsTo == players[0].n:
                bullets.remove(bullet)
        for player in players:
            removebullets = pygame.sprite.spritecollide(player.spr, bullets, False, pygame.sprite.collide_circle)
            for bullet in removebullets:
                if bullet.belongsTo == players[0].n:
                    sparks.append(Spark(bullet.pos))
                    bullets.remove(bullet)
                    if player == players[1]:  # but did we hit the other player or ourselves?
                        if SINGLEPLAYER:
                            players[1].health = max(0, players[1].health - settings['Bullet.damage'].val)
                        else:
                            hitsdealt += 1
                    else:
                        players[0].health = max(0, players[0].health - settings['Bullet.damage'].val)

        for spark in sparks:
            spark.updateAndDraw(screen)

        bullets.draw(screen)
        for bulletpos in remotebullets:
            pygame.draw.circle(screen, Bullet.COLOR, bulletpos, settings['Bullet.size'].val)

        players[0].update()
        if SINGLEPLAYER:
            players[1].update()

        for player in players:
            player.draw(screen)

            w, h = player.spr.rect.width, player.spr.rect.height
            x, y = player.spr.rect.center
            idis = h * Player.INDICATORDISTANCE

            # Draw battery level indicators
            bl = player.batterylevel / settings['Player.battSize'].val
            poweryellow = (255, 200, 0)
            if player.batterylevel < settings['Player.thrust'].val / settings['Player.thrust/kJ'].val:
                indicatorcolor = (255, 0, 0)
            elif player.batterylevel < settings['Player.kJ/shot'].val:
                indicatorcolor = (255, 128, 0)
            else:
                indicatorcolor = poweryellow
            # outer rectangle
            pygame.draw.rect(screen, indicatorcolor, (roundi(x - w - 1), roundi(player.pos.y + h + idis + 1), roundi((w * 2 + 2)), roundi(h * Player.INDICATORHEIGHT + 2)))
            # inner black area (same area as above but -1px on each side)
            pygame.draw.rect(screen, (  0,   0,  0), (roundi(x - w - 0), roundi(player.pos.y + h + idis + 2), roundi((w * 2 + 0)), roundi(h * Player.INDICATORHEIGHT + 0)))
            # battery level (drawn over the black area)
            pygame.draw.rect(screen, poweryellow   , (roundi(x - w - 0), roundi(player.pos.y + h + idis + 2), roundi((w * 2 + 0) * bl), roundi(h * Player.INDICATORHEIGHT + 0)))

            # Draw health indicators
            healthgreen = (10, 230, 10)
            indicatorcolor = healthgreen if player.health > settings['Bullet.damage'].val else (255, 100, 0)
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
            msg = b'\x00' + mplib.updatestruct.pack(
                players[0].seqno,
                roundi(min(SCREENSIZE[0] + 1000, max(-1000, players[0].pos.x))),
                roundi(min(SCREENSIZE[1] + 1000, max(-1000, players[0].pos.y))),
                roundi(min(1000, max(-1000, players[0].speed.x * 100))),
                roundi(min(1000, max(-1000, players[0].speed.y * 100))),
                roundi(players[0].angle / 1.5),
                roundi(players[0].batterylevel / settings['Player.battSize'].val * 255),
                roundi(players[0].health * 255),
                hitsdealt,
            )
            for bullet in bullets:
                msg += mplib.bulletstruct.pack(roundi(bullet.pos.x), roundi(bullet.pos.y))
            players[0].seqno += 1
            hitsdealt = 0
            sendtoQueued(msg)

            nextPingAt -= 1
            if nextPingAt <= 0:
                sendtoQueued(b'\x02')
                pingSentAt = time.time()
                nextPingAt = random.randint(FPS * (PINGEVERY / 2), FPS * (PINGEVERY * 2))
    elif state == STATE_DEAD:
        if keystates[pygame.K_RETURN]:
            score += gamescore
            if SINGLEPLAYER:
                state = STATE_PLAYERING
                initSinglePlayer()
                statusmessage = ''
            else:
                sock.sendto(mplib.playerquits + mplib.restartpl0x, SERVER)
                state = STATE_INITIAL

    if SIMPLEGRAPHICS:  # draw circle non-anti-aliased: 31µs; blit regular surface: 288-600µs; blit converted surface with alpha: ~60µs
        pygame.draw.circle(screen, (255, 255, 0), gravitywell_center_int, 50)
    else:
        screen.blit(gravitywell, gravitywellrect)

    if len(statusmessage) > 0:
        msgpart = statusmessage[0 : int(time.time() * len(statusmessage)) % (len(statusmessage) * 2)]
        surface = font_statusMsg.render(msgpart, True, (0, 30, 174))
        screen.blit(surface, (10, 50))

    pygame.display.flip()
    frametime = fpslimiter.tick(FPS)
    if frametime * 0.9 > FRAMETIME * 1000:  # 10% margin because it will sleep longer sometimes to keep the fps *below* the target amount
        print('frametime was', frametime)

