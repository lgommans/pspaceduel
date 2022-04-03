#!/usr/bin/env python3

import sys, os, math, time, random, socket, threading
import pygame
import mplib
from settings import Setting, settings, prefs
from luclib import *

class Spark:
    def __init__(self, pos):
        self.pos = pygame.math.Vector2(pos)
        self.lifespan = random.randint(*prefs['Spark.lifespan'])
        self.angle = random.randint(0, 360)
        self.rotation = random.randint(*prefs['Spark.rotation']) * (-1 if random.randint(1, 2) == 1 else 1)

    def updateAndDraw(self, screen):
        # returns whether it needs to be destroyed

        self.lifespan -= 1
        if self.lifespan <= 0:
            return True

        self.pos.x += random.randint(*prefs['Spark.movement']) * (-1 if random.randint(1, 2) == 1 else 1)
        self.pos.y += random.randint(*prefs['Spark.movement']) * (-1 if random.randint(1, 2) == 1 else 1)
        self.angle += self.rotation

        rotated_image = pygame.transform.rotate(Spark.IMAGE, self.angle)
        screen.blit(rotated_image, coordsToPx(roundi(self.pos.x), roundi(self.pos.y)))


class Bullet(pygame.sprite.Sprite):
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
            pygame.draw.circle(self.image, prefs['Bullet.color'], (bulletsize, bulletsize), bulletsize)
            self.image = self.image.convert_alpha()

    def advance(self):
        # Returns whether it should be removed (out of screen, fell into gravity well; no health-bearing-object collisions)

        accelx, accely, separation = gravity(self.pos, ZEROVECTOR, settings['Bullet.mass'].val, settings['GW.mass'].val)
        self.speed.x -= accelx
        self.speed.y -= accely
        self.pos.x += self.speed.x
        self.pos.y += self.speed.y
        if not self.virtual:
            self.rect.center = (roundi(self.pos.x), roundi(self.pos.y))

        if game.players[0].n == self.belongsTo and separation < settings['GW.radius'].val:  # GW assumed to be spherical
            return True

        if self.pos.x < -(SCREENSIZE[0] / 2) - ((SCREENSIZE[0] / 2) * Bullet.MAX_OUT_OF_SCREEN) or self.pos.x > (SCREENSIZE[0] / 2) + (SCREENSIZE[0] / 2 * Bullet.MAX_OUT_OF_SCREEN) \
        or self.pos.y < -(SCREENSIZE[1] / 2) - ((SCREENSIZE[1] / 2) * Bullet.MAX_OUT_OF_SCREEN) or self.pos.y > (SCREENSIZE[1] / 2) + (SCREENSIZE[1] / 2 * Bullet.MAX_OUT_OF_SCREEN):
            return True

        return False


class Player:
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
        self.hitsdealt = 0

    def thrust(self):
        if self.batterylevel > settings['Player.thrust'].val / settings['Player.thrust/kJ'].val:
            self.speed.x += lengthdir_x(settings['Player.thrust'].val * FRAMETIME / settings['Player.mass'].val, self.angle)
            self.speed.y += lengthdir_y(settings['Player.thrust'].val * FRAMETIME / settings['Player.mass'].val, self.angle)
            self.batterylevel -= settings['Player.thrust'].val / settings['Player.thrust/kJ'].val

    def draw(self, screen):
        self.spr.rect.left = roundi(self.pos.x)
        self.spr.rect.top = roundi(self.pos.y)

        blitRotateCenter(screen, self.img, coordsToPx(roundi(self.spr.rect.left), roundi(self.spr.rect.top)), self.angle)

    def rotate(self, direction, fine=False):  # direction is 1 or -1
        if direction == 0:
            return

        rotationamount = direction * (prefs['Player.rotate_speed'] if not fine else prefs['Player.rotate_speed_fine'])
        if self.batterylevel > abs(rotationamount) / settings['Player.rot/kJ'].val:
            self.batterylevel -= abs(rotationamount) / settings['Player.rot/kJ'].val
            self.angle += rotationamount
            self.angle %= 360
            rotated_image = pygame.transform.rotate(self.img, self.angle)
            self.spr.mask = pygame.mask.from_surface(rotated_image)

    def update(self):  # this function should only be run on the local player while in multiplayer mode, since it calls playerDied which triggers network events
        if self.health <= 0:
            if game.singleplayer and self == game.players[1]:
                game.playerDied(other=True)
            else:
                game.playerDied(other=False)
            return

        if self.reloadstate > FPS * settings['Player.reload'].val * settings['Player.minreload'].val:
            self.reloadstate -= 1

        # It is assumed that the 'towards' object is at a fixed position (a gravity well). It will not be updated according to forces felt
        accelx, accely, separation = gravity(pygame.math.Vector2(self.spr.rect.center), ZEROVECTOR, settings['Player.mass'].val, settings['GW.mass'].val)
        self.speed.x -= accelx
        self.speed.y -= accely
        self.pos.x += self.speed.x
        self.pos.y += self.speed.y

        if separation < (settings['GW.radius'].val) + (self.spr.rect.width / 2):  # GW assumed to be spherical
            if game.singleplayer and self == game.players[1]:
                game.playerDied(other=True)
            else:
                game.playerDied(other=False)
            return

        if self.pos.x < settings['Player.visiblepx'].val - self.spr.rect.width - (SCREENSIZE[0] / 2):
            self.pos.x = (SCREENSIZE[0] / 2) - settings['Player.visiblepx'].val
        elif self.pos.x > (SCREENSIZE[0] / 2) - settings['Player.visiblepx'].val:
            self.pos.x = settings['Player.visiblepx'].val - self.spr.rect.width - (SCREENSIZE[0] / 2)

        if self.pos.y < settings['Player.visiblepx'].val - self.spr.rect.height - (SCREENSIZE[1] / 2):
            self.pos.y = (SCREENSIZE[1] / 2) - settings['Player.visiblepx'].val
        elif self.pos.y > (SCREENSIZE[1] / 2) - settings['Player.visiblepx'].val:
            self.pos.y = settings['Player.visiblepx'].val - self.spr.rect.height - (SCREENSIZE[1] / 2)

        if pygame.sprite.collide_mask(game.players[0].spr, game.players[1].spr) is not None:
            # If you run into each other, you both die. Should have run, you fools
            game.playerDied(both=True)

        radiative_power = settings['GW.radiation'].val / (separation * separation) * 1000
        self.batterylevel = min(settings['Player.battSize'].val, self.batterylevel + radiative_power)


class Game:
    def __init__(self, singleplayer):
        self.singleplayer = singleplayer

        self.score = 0
        self.roundscore = 0
        self.players = [
            Player(1),
            Player(2),
        ]

        if not singleplayer:
            self.stopSendtoThread = False
            self.msgQueue = []  # apparently a regular list is thread-safe in python in 2022
            self.msgQueueEvent = threading.Event()
            threading.Thread(target=self.sendto).start()

        self.newRound()

    def playerDied(self, other=False, both=False, sendpacket=True):
        # other: did the other player die or did we die?
        global statusmessage

        self.state = STATE_DEAD

        if both:
            self.roundscore = 1
            statusmessage = 'You tied: 1 point! Your score: ' + str(self.score + self.roundscore) + '. Press Enter to restart.'
            if not game.singleplayer and sendpacket:
                self.sendtoQueued(b'\x01\x01')
        else:
            if other:
                self.roundscore = 5
                statusmessage = 'You won: 5 points! Your score: ' + str(self.score + self.roundscore) + '. Press Enter to restart.'
            else:
                self.roundscore = 0
                statusmessage = 'You died. Your score: ' + str(self.score) + '. Press Enter to restart.'
                if not game.singleplayer and sendpacket:
                    self.sendtoQueued(b'\x01')

    def newRound(self):
        if self.roundscore > 0:
            self.score += self.roundscore

        self.sparks = []
        self.bullets = pygame.sprite.Group()
        self.remotebullets = []
        self.roundscore = 0
        self.players[0].reinitialize()
        self.players[1].reinitialize()

    def connect(self, server):
        global statusmessage

        self.server = server
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(0)
        self.sock.sendto(mplib.clienthello, server)  # using sendtoQueued() here makes recvfrom() give an error on Windows
        self.state = STATE_HELLOSENT
        statusmessage = 'Waiting for server initial response...'

    def sendto(self):
        while True:
            if len(self.msgQueue) == 0:
                # Doing this thread blocking/unblocking is ~13× faster than starting a new thread for every packet
                self.msgQueueEvent.clear()
                self.msgQueueEvent.wait()

            if self.stopSendtoThread:
                return

            try:
                msg = self.msgQueue.pop(0)
                self.sock.sendto(msg, self.server)
            except IndexError:
                # We somehow managed to try and pop an empty list
                print('moin? We were asked to send something but there is nothing in the queue? Going back to sleep...')


    def sendtoQueued(self, msg):
        self.msgQueue.append(msg)
        self.msgQueueEvent.set()

    def stopMultiplayer(self, reason):
        self.sock.sendto(mplib.playerquits + reason.encode('ASCII'), self.server)
        self.stopSendtoThread = True
        self.msgQueueEvent.set()
        self.nextPingAt = None

    def processIncomingPacket(self, msg):
        global statusmessage

        if self.state == STATE_HELLOSENT:
            if msg[0 : len(mplib.serverhello)] != mplib.serverhello:
                statusmessage = 'Server protocol error, please restart the game.'
            else:
                mptoken = msg[len(mplib.serverhello) : ]
                self.sendtoQueued(mptoken)
                self.state = STATE_TOKENSENT
                statusmessage = 'Completing server handshake...'

                self.newRound()
                self.schedulePing()

                self.players[0].seqno += 1


        elif self.state == STATE_TOKENSENT:
            if msg == mplib.urplayerone:
                statusmessage = 'Server connection established. Waiting for another player to join this server...'
                self.players[0].n = 1
                self.players[1].n = 2
            elif msg == mplib.playerfound:
                self.state = STATE_MATCHED
                reply = mplib.settingsmsg + Setting.serializeSettings(settings)
                self.sock.sendto(reply, SERVER)
                self.sock.sendto(reply, ('127.0.0.1', self.sock.getsockname()[1]))  # also send it to ourselves
            elif msg == mplib.urplayertwo:
                statusmessage = 'Server found a match! Waiting for the other player to send game data...'
                self.players[0].n = 2
                self.players[1].n = 1
                self.state = STATE_MATCHED
            else:
                statusmessage = 'Server protocol error, please restart the game.'
                print('Got from server:', msg)

        elif self.state == STATE_MATCHED:
            if msg[ : len(mplib.settingsmsg)] != mplib.settingsmsg:
                print('Waiting for initial setup data, got this instead: ', msg)
                return

            Setting.updateSettings(settings, msg[len(mplib.settingsmsg) : ])

            gravitywell.setImage(settings['GW.imagenumber'].val)
            halfpw = self.players[0].spr.rect.width / 2
            halfph = self.players[0].spr.rect.height / 2
            self.players[self.players[0].n - 1].pos = pygame.math.Vector2(settings['Player1.x'].val - halfpw, settings['Player1.y'].val - halfph)
            self.players[self.players[0].n - 1].speed = pygame.math.Vector2(settings['Player1.xspeed'].val, settings['Player1.yspeed'].val)
            self.players[self.players[1].n - 1].pos = pygame.math.Vector2(settings['Player2.x'].val - halfpw, settings['Player2.y'].val - halfph)
            self.players[self.players[1].n - 1].speed = pygame.math.Vector2(settings['Player2.xspeed'].val, settings['Player2.yspeed'].val)
            self.players[0].draw(screen)  # updates the sprite, which also does collision detection, to prevent collision on frame 0
            self.state = STATE_PLAYERING
            statusmessage = ''

        elif self.state in (STATE_PLAYERING, STATE_DEAD):
            if msg.startswith(mplib.playerquits):
                reason = msg[len(mplib.playerquits) : ]
                if reason == mplib.restartpl0x:
                    statusmessage += ' The other player restarted!'
                else:
                    if self.state == STATE_PLAYERING:
                        statusmessage = 'You win with score ' + str(self.score) + '! The other player ' + str(reason, 'ASCII')
                    else:
                        statusmessage = 'The other player ' + str(reason, 'ASCII') + '. Your score was: ' + str(self.score)
            elif msg[0] == 0:
                seqno, x, y, xspeed, yspeed, angle, batlvl, health, hitsfromtheirbullets = mplib.updatestruct.unpack(msg[1 : 1 + mplib.updatestruct.size])
                if seqno <= self.players[1].seqno:
                    print('Ignored seqno', seqno, ' because the last seqno for this player was', self.players[1].seqno)
                else:
                    if seqno - 1 != self.players[1].seqno:
                        print('Info: jitter or loss. Received seqno', seqno, ' whereas the last seqno for this player was', self.players[1].seqno)
                    self.players[1].seqno = seqno
                    self.players[1].angle = angle * 1.5
                    self.players[1].pos = pygame.math.Vector2(x, y)
                    self.players[1].speed = pygame.math.Vector2(xspeed / 100, yspeed / 100)
                    self.players[1].batterylevel = batlvl / 255 * settings['Player.battSize'].val
                    self.players[1].health = health / 255

                    if hitsfromtheirbullets > 0:
                        self.players[0].health = max(0, self.players[0].health - (settings['Bullet.damage'].val * hitsfromtheirbullets))
                        for _ in range(hitsfromtheirbullets):
                            self.sparks.append(Spark(self.players[0].pos))

                    msg = msg[1 + mplib.updatestruct.size : ]
                    self.remotebullets = []
                    while len(msg) > 0:
                        x, y = mplib.bulletstruct.unpack(msg[ : mplib.bulletstruct.size])
                        self.remotebullets.append((x, y))
                        msg = msg[mplib.bulletstruct.size : ]

            elif msg[0] == 1:
                if len(msg) > 1 and msg[1] == 1:
                    self.playerDied(both=True, sendpacket=False)
                else:
                    self.playerDied(other=True)

            elif msg[0] == 2:
                self.sendtoQueued(b'\x03')

            elif msg[0] == 3:
                if self.pingSentAt is not None:
                    ping = (time.time() - self.pingSentAt) * 1000  # ms
                    print('Ping time:', round(ping), 'ms')
                    self.pingSentAt = None
                    self.schedulePing()

    def sendUpdatePacket(self):
        if self.singleplayer:
            return

        msg = b'\x00' + mplib.updatestruct.pack(
            self.players[0].seqno,
            roundi(min(SCREENSIZE[0] + 1000, max(-1000, self.players[0].pos.x))),
            roundi(min(SCREENSIZE[1] + 1000, max(-1000, self.players[0].pos.y))),
            roundi(min(1000, max(-1000, self.players[0].speed.x * 100))),
            roundi(min(1000, max(-1000, self.players[0].speed.y * 100))),
            roundi(self.players[0].angle / 1.5),
            roundi(self.players[0].batterylevel / settings['Player.battSize'].val * 255),
            roundi(self.players[0].health * 255),
            self.players[0].hitsdealt,
        )
        for bullet in self.bullets:
            msg += mplib.bulletstruct.pack(roundi(bullet.pos.x), roundi(bullet.pos.y))
        self.sendtoQueued(msg)
        self.players[0].seqno += 1
        self.players[0].hitsdealt = 0

        if self.nextPingAt is not None:
            self.nextPingAt -= 1
            if self.nextPingAt <= 0:
                self.sendtoQueued(b'\x02')
                pingSentAt = time.time()

    def schedulePing(self):
        # game step countdown
        self.nextPingAt = random.randint(FPS * (prefs['Multiplayer.pinginterval'] / 2), FPS * (prefs['Multiplayer.pinginterval'] * 2))
        self.pingSentAt = None

    def recvFromNetwork(self):
        for _ in range(15):  # process up to N packets per frame (send rate is only ~1.01 packets per frame, this is for catching up / jitter)
            try:
                msg, addr = self.sock.recvfrom(mplib.maximumsize)
            except BlockingIOError:
                msg = b''

            if msg == b'':
                break  # no (more) data from the network
            else:
                self.processIncomingPacket(msg)


class GravityWell:
    def __init__(self):
        self.image = None

    def setImage(self, imagenumber):
        if prefs['Game.simple_graphics']:
            return

        try:
            if imagenumber == 1:
                self.image = pygame.image.load('res/yellow-sphere.png').convert_alpha()
                self.frames = None
            elif imagenumber == 2:
                self.image = pygame.image.load('res/sun.png').convert_alpha()
                self.frames = None
            elif imagenumber == 3:
                self.frames = loadGIF('res/earth-scaled-fixedforPIL.gif')
                self.image = self.frames[0]
            else:
                print('Note: GravityWell image number', imagenumber, 'was requested but we do not have it.')

            self.framecounter = 0  # in case it needs resetting
            GWwidth = roundi(settings['GW.radius'].val * 2)
            if self.image.get_rect().width != GWwidth:
                wh = (GWwidth, GWwidth)  # since it's spherical... width,height == width,width
                if self.frames is not None:
                    for i, frame in enumerate(self.frames):
                        self.frames[i] = pygame.transform.scale(frame, wh)
                else:
                    self.image = pygame.transform.scale(self.image, wh)

            if self.frames is not None:
                self.image = self.frames[0]
        except Exception as e:  # might fail if PIL is not installed and a GIF was requested. Not bad, just use the default...
            print('Warning:', type(e).__name__, 'while loading GW image')
            return

    def animationStep(self):
        if self.frames is None:
            return

        self.framecounter += 1
        self.framecounter %= len(self.frames) * 8
        self.image = self.frames[self.framecounter // 8]


def gravity(obj1pos, obj2pos, obj1mass, obj2mass):
    separation_x = obj1pos.x - obj2pos.x
    separation_y = obj1pos.y - obj2pos.y
    separation_square = (separation_x * separation_x) + (separation_y * separation_y)
    grav_accel = obj1mass * obj2mass / separation_square * (FRAMETIME * GRAVITYCONSTANT)
    separation = math.sqrt(separation_square)
    dir_x = separation_x / separation
    dir_y = separation_y / separation
    return grav_accel / obj1mass * dir_x, grav_accel / obj1mass * dir_y, separation


def roundi(n):  # because pygame wants an int and round() returns a float for some reason but int() drops the fractional part... pain in the bum, here's a shortcut...
    return int(round(n))


def blitRotateCenter(surf, image, pos, angle):
    # this function is CC-BY-SA 4.0 by Rabbid76 from https://stackoverflow.com/a/54714144
    rotated_image = pygame.transform.rotate(image, angle)
    new_rect = rotated_image.get_rect(center=image.get_rect(topleft = pos).center)
    surf.blit(rotated_image, new_rect)


def quitProgram(reason, exitstatus=0):
    if not game.singleplayer:
        game.stopMultiplayer(reason)

    sys.exit(exitstatus)


def prepareHostAndPort(hostAndPort, defaultport=9473):
    # Parse into an (IP, port) tuple for passing to socket.sendto() or socket.connect()

    if ':' not in hostAndPort:
        hostOrIP = hostAndPort
        port = defaultport
    else:
        hostOrIP, port = hostAndPort.split(':', 1)
        port = int(port)

    try:
        ip = socket.gethostbyname(hostOrIP)
    except Exception as e:
        print('Error looking up server name to get an IP, might you not have Internet or might the DNS server be down?')
        raise e

    return (ip, port)


def initSinglePlayer():
    halfpw = game.players[0].spr.rect.width / 2
    halfph = game.players[0].spr.rect.height / 2
    game.players[0].pos = pygame.math.Vector2(settings['Player1.x'].val - halfpw, settings['Player1.y'].val - halfph)
    game.players[0].speed = pygame.math.Vector2(settings['Player1.xspeed'].val, settings['Player1.yspeed'].val)
    game.players[0].draw(screen)  # updates the sprite position to avoid a collision with player 2
    game.players[1].pos = pygame.math.Vector2(settings['Player2.x'].val - halfpw, settings['Player2.y'].val - halfph)
    game.players[1].speed = pygame.math.Vector2(settings['Player2.xspeed'].val, settings['Player2.yspeed'].val)
    game.players[1].draw(screen)
    game.newRound()
    game.state = STATE_PLAYERING
    gravitywell.setImage(settings['GW.imagenumber'].val)


def loadGIF(filename):
    global imported_PIL, Image, ImageSequence

    if not imported_PIL:
        from PIL import Image, ImageSequence
        imported_PIL = True

    # Function ©Rabbid76, <https://stackoverflow.com/a/64668964/1201863>, CC BY-SA
    img = Image.open(filename)
    frames = []
    for frame in ImageSequence.Iterator(img):
        frame = frame.convert('RGBA')
        pygameImage = pygame.image.fromstring(frame.tobytes(), frame.size, frame.mode).convert_alpha()
        frames.append(pygameImage)
    return frames


def coordsToPx(x, y):
    return (x + (SCREENSIZE[0] // 2), y + (SCREENSIZE[1] // 2))


def parseArgs(argv):
    if '-h' in argv or '--help' in argv:
        print('''
Usage:
    {me}
       Play the game online with default settings.
    {me} <hostname>
       Connect to a different server.
    {me} <hostname:port>
       Connect to a different server at a specific port.
    {me} --singleplayer
       Play a dummy game offline. Mainly for testing purposes.

For settings, see `settings.py`.
For how to play, see `README.txt`.
For running a server, see `server.py`.
'''.lstrip().format(me=os.path.basename(argv[0])))
        sys.exit(1)

    args = {
        'singleplayer': False,
        'server':       None,
    }

    if '--singleplayer' in argv:
        args['singleplayer'] = True
    elif len(argv) == 2:
        args['server'] = argv[1]

    return args


GRAVITYCONSTANT = 6.6742e-11
SCREENSIZE = (1900, 980)
FPS = 60
FRAMETIME = 1 / FPS
FTGC = FRAMETIME * GRAVITYCONSTANT
ZEROVECTOR = pygame.math.Vector2(0, 0)

STATE_INITIAL   = 0
STATE_HELLOSENT = 1
STATE_TOKENSENT = 2
STATE_MATCHED   = 3
STATE_PLAYERING = 4
STATE_DEAD      = 5

args = parseArgs(sys.argv)

# don't just pygame.init() because it will hang and not quit when you do pygame.quit();sys.exit();. Stackoverflow suggests in 2013 this was a Wheezy bug, but it works on a
# newer-than-Wheezy system, and then does not work on an even newer system than that, so... initializing only what we need is also literally 20 times faster (0.02 instead of 0.4 s)!
pygame.display.init()
pygame.font.init()
font_statusMsg = pygame.font.SysFont(None, 48)
fpslimiter = pygame.time.Clock()
screen = pygame.display.set_mode(SCREENSIZE)
imported_PIL = False
statusmessage = ''

if not args['singleplayer']:
    # if dns lookup is needed, do this now (works also if you enter an IP, gethostbyname will just return it literally)
    # else sock.sendto() will do dns lookup for every call and, depending on the setup, that might hit the network for sending each individual update packet
    if args['server'] is not None:
        SERVER = prepareHostAndPort(args['server'])
    else:
        SERVER = prepareHostAndPort(prefs['Multiplayer.server'])

Spark.IMAGE = pygame.image.load(prefs['Spark.graphic']).convert_alpha()

if not prefs['Game.simple_graphics'] and prefs['Game.backgroundimage'] is not None:
    bgimg = pygame.image.load(prefs['Game.backgroundimage']).convert_alpha()

game = Game(singleplayer=args['singleplayer'])
gravitywell = GravityWell()

if game.singleplayer:
    initSinglePlayer()
else:
    game.connect(SERVER)

while True:
    if not game.singleplayer:
        game.recvFromNetwork()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            quitProgram(reason='fled the arena')
    keystates = pygame.key.get_pressed()

    if keystates[pygame.K_ESCAPE]:
        quitProgram(reason='escaped the arena')

    if prefs['Game.simple_graphics'] or prefs['Game.backgroundimage'] is None:
        screen.fill((0, 0, 0))
    else:
        screen.blit(bgimg, (0, 0))

    if prefs['Game.simple_graphics'] or gravitywell.image is None:  # draw circle non-anti-aliased: 31µs; blit regular surface: 288-600µs; blit converted surface with alpha: ~60µs
        pygame.draw.circle(screen, (255, 255, 0), coordsToPx(0, 0), 50)
    else:
        screen.blit(gravitywell.image, coordsToPx(-settings['GW.radius'].val, -settings['GW.radius'].val))
        gravitywell.animationStep()

    if game.state == STATE_PLAYERING:
        game.players[0].rotate(keystates[pygame.K_LEFT] - keystates[pygame.K_RIGHT], keystates[pygame.K_LSHIFT] or keystates[pygame.K_RSHIFT])

        if keystates[pygame.K_SPACE]:
            if game.players[0].reloadstate <= 0 and game.players[0].batterylevel > settings['Player.kJ/shot'].val:
                game.players[0].reloadstate += FPS * settings['Player.reload'].val
                game.players[0].batterylevel -= settings['Player.kJ/shot'].val
                game.bullets.add(Bullet(game.players[0]))

        if keystates[pygame.K_UP]:
            game.players[0].thrust()

        removebullets = []
        for bullet in game.bullets:
            if bullet.belongsTo == game.players[0].n:
                died = bullet.advance()
                if died:
                    removebullets.append(bullet)
        for bullet in removebullets:
            if bullet.belongsTo == game.players[0].n:
                game.bullets.remove(bullet)
        for player in game.players:
            removebullets = pygame.sprite.spritecollide(player.spr, game.bullets, False, pygame.sprite.collide_circle)
            for bullet in removebullets:
                if bullet.belongsTo == game.players[0].n:
                    game.sparks.append(Spark(bullet.pos))
                    game.bullets.remove(bullet)
                    if player == game.players[1]:  # but did we hit the other player or ourselves?
                        if game.singleplayer:
                            game.players[1].health = max(0, game.players[1].health - settings['Bullet.damage'].val)
                        else:
                            game.players[0].hitsdealt += 1
                    else:
                        game.players[0].health = max(0, game.players[0].health - settings['Bullet.damage'].val)

        removesparks = []
        for spark in game.sparks:
            died = spark.updateAndDraw(screen)
            if died:
                removesparks.append(spark)
        for spark in removesparks:
            game.sparks.remove(spark)

        for bulletpos in game.remotebullets + [bullet.rect.center for bullet in game.bullets]:
            pygame.draw.circle(screen, prefs['Bullet.color'], coordsToPx(*bulletpos), settings['Bullet.size'].val)

        game.players[0].update()
        if game.singleplayer:
            game.players[1].update()

        for player in game.players:
            player.draw(screen)

            w, h = player.spr.rect.width, player.spr.rect.height
            x, y = player.spr.rect.center
            idis = h * prefs['Player.indicator_distance']

            # Draw battery level indicators
            bl = player.batterylevel / settings['Player.battSize'].val
            bgcol = prefs['Player.indicator_energy_color_bg']
            poweryellow = prefs['Player.indicator_energy_color_good']
            if player.batterylevel < settings['Player.thrust'].val / settings['Player.thrust/kJ'].val:
                indicatorcolor = prefs['Player.indicator_energy_color_out']
            elif player.batterylevel < settings['Player.kJ/shot'].val:
                indicatorcolor = prefs['Player.indicator_energy_color_low']
            else:
                indicatorcolor = poweryellow
            # outer rectangle
            pygame.draw.rect(screen, indicatorcolor, (*coordsToPx(roundi(x - w - 1), roundi(player.pos.y + h + idis + 1)), roundi((w * 2 + 2)),      roundi(h * prefs['Player.indicator_height'] + 2)))
            # inner black area (same area as above but -1px on each side)
            pygame.draw.rect(screen, bgcol,          (*coordsToPx(roundi(x - w - 0), roundi(player.pos.y + h + idis + 2)), roundi((w * 2 + 0)),      roundi(h * prefs['Player.indicator_height'] + 0)))
            # battery level (drawn over the black area)
            pygame.draw.rect(screen, poweryellow   , (*coordsToPx(roundi(x - w - 0), roundi(player.pos.y + h + idis + 2)), roundi((w * 2 + 0) * bl), roundi(h * prefs['Player.indicator_height'] + 0)))

            # Draw health indicators
            healthgreen = prefs['Player.indicator_health_color_good']
            indicatorcolor = healthgreen if player.health > settings['Bullet.damage'].val else prefs['Player.indicator_health_color_low']
            bgcol = prefs['Player.indicator_health_color_bg']
            # outer rectangle
            pygame.draw.rect(screen, indicatorcolor, (*coordsToPx(roundi(x - w - 1), roundi(player.pos.y - idis - 2)), roundi((w * 2 + 2)),                 roundi(h * prefs['Player.indicator_height'] + 2)))
            # inner black area (same area as above but -1px on each side)
            pygame.draw.rect(screen, bgcol,          (*coordsToPx(roundi(x - w - 0), roundi(player.pos.y - idis - 1)), roundi((w * 2 + 0)),                 roundi(h * prefs['Player.indicator_height'] + 0)))
            # health level (drawn over the black area)
            pygame.draw.rect(screen, healthgreen,    (*coordsToPx(roundi(x - w - 0), roundi(player.pos.y - idis - 1)), roundi((w * 2 + 0) * player.health), roundi(h * prefs['Player.indicator_height'] + 0)))

        if prefs['Game.show_aim_guide']:
            b = Bullet(game.players[0], virtual=True)
            for i in range(prefs['Game.aim_guide_distance']):
                oldpos = pygame.math.Vector2(b.pos)
                died = b.advance()
                if died:
                    break
                pygame.draw.line(screen, prefs['Game.aim_guide_color'], coordsToPx(*oldpos), coordsToPx(*b.pos))


        game.sendUpdatePacket()
    elif game.state == STATE_DEAD:
        if keystates[pygame.K_RETURN]:
            if game.singleplayer:
                initSinglePlayer()
                statusmessage = ''
            else:
                game.sock.sendto(mplib.playerquits + mplib.restartpl0x, SERVER)
                game.connect(SERVER)

    if len(statusmessage) > 0:
        msgpart = statusmessage[0 : int(time.time() * len(statusmessage)) % (len(statusmessage) * 2)]
        surface = font_statusMsg.render(msgpart, True, prefs['Game.text_color'])
        screen.blit(surface, prefs['Game.text_position'])

    pygame.display.flip()
    frametime = fpslimiter.tick(FPS)
    if frametime * 0.9 > FRAMETIME * 1000:  # 10% margin because it will sleep longer sometimes to keep the fps *below* the target amount
        print('frametime was', frametime)

