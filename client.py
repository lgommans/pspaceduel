#!/usr/bin/env python3
# TODO add bullet accuracy statistics
# TODO if you die on someone's spawn position then you collide on the first frame

import sys, os, math, time, random, socket, threading, importlib
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'  # suppresses "Hello from the pygame community. <url>" every time you run the binary. Not to hide that we're using pygame, of course, but I regularly look at the output and this is additional clutter
import pygame
import src.mplib as mplib
import src.botlib as botlib
from settings import Setting, settings, prefs
from src.luclib import *
from src.spark import Spark
from src.body import Body
from src.gravity_well import GravityWell
from src.bullet import Bullet
from src.game_state import GameState

def update_fps():
    global frame_time_budget, simulation_time_step

    frame_time_budget = 1 / settings['Game.FPS'].val
    simulation_time_step = frame_time_budget * settings['Game.speed'].val


class Player(Body):
    def __init__(self, n, game, bot=None):
        """
        Parameters:
          n: the player number (int)
          game: the instance of the game object which is initialising this player
          bot: str or None. If string, it must be an importable Python module (bot="bots.myAI" will try to include "./bots/myAI.py").
              The game will call bot.reset(player) when a round is about to start (also the first round), passing the object of the player character which the bot controls.
              The game will call bot.step(game) every time you may make a decision about what to do. Use the game state to make a decision and return an action list.
              The action list must consist of zero or more values from botlib.Action; repetitions within the same list have no effect.
              The game state ('game' parameter for bot.step) is currently just the game object, which can be used to cheat. Assume that future versions present a read-only copy.
              If a bot raises any exception, the game is undecided (neither drawn, won, nor lost). It is up to the person running the game to handle this situation.
        """
        img = pygame.image.load(f'res/player{n}.png')
        rect = img.get_rect()

        self.n = n
        self.game = game
        self.seqno = 0

        self.img = pygame.transform.scale(img, (roundi(rect.width * settings['Player.scale'].val), roundi(rect.height * settings['Player.scale'].val)))
        self.img = self.img.convert_alpha()
        self.spr = pygame.sprite.Sprite()
        self.spr.rect = self.img.get_rect()
        self.spr.mask = pygame.mask.from_surface(self.img)
        # the maximum width/height we can have as we rotate 0-360 degrees
        self.rotatedMaxSize = max(self.spr.rect.width, self.spr.rect.height)

        Body.__init__(self)

        if bot is None:
            self.bot = None
        else:
            self.bot = importlib.import_module(bot)
        self.reset()

    def reset(self):
        self.angle = 0  # 0-360
        self.health = 1  # 0-1
        self.batterylevel = settings['Player.battSize'].val
        self.reloadstate = 0
        self.hitsdealt = 0
        self.seqno = 0
        self.updateRotatedSprite()
        if self.bot is not None:
            self.bot.reset(self)

    def tryShoot(self):
        if self.reloadstate <= 0 and self.batterylevel > settings['Player.kJ/shot'].val:
            self.reloadstate += settings['Game.FPS'].val * settings['Player.reload'].val
            self.batterylevel -= settings['Player.kJ/shot'].val
            self.game.bullets.add(Bullet(self))

    def thrust(self, fine=False):
        # TODO animation? Or leave the ion engine exhaust invisible?

        if fine:
            finefactor = prefs['Player.thrust_factor_fine']
        else:
            finefactor = 1

        energyNeeded = settings['Player.thrust'].val / settings['Player.thrust/kJ'].val * finefactor

        if self.batterylevel > energyNeeded:
            self.speed.x += lengthdir_x(settings['Player.thrust'].val * simulation_time_step / self.mass * finefactor, self.angle)
            self.speed.y += lengthdir_y(settings['Player.thrust'].val * simulation_time_step / self.mass * finefactor, self.angle)
            self.batterylevel -= energyNeeded

    def draw(self, screen):
        self.spr.rect.center = (roundi(self.pos.x), roundi(self.pos.y))

        new_rect = self.rotated_image.get_rect(center=coordsToPx(*self.pos))
        screen.blit(self.rotated_image, new_rect)

    def rotate(self, direction, fine=False):  # direction is 1 or -1
        if direction == 0:
            return

        rotationamount = direction * (prefs['Player.rotate_speed'] if not fine else prefs['Player.rotate_speed_fine'])
        if self.batterylevel > abs(rotationamount) / settings['Player.rot/kJ'].val:
            self.batterylevel -= abs(rotationamount) / settings['Player.rot/kJ'].val
            self.angle += rotationamount
            self.angle %= 360
            self.updateRotatedSprite()

    def updateRotatedSprite(self):
        self.rotated_image = pygame.transform.rotate(self.img, self.angle)
        self.spr.mask = pygame.mask.from_surface(self.rotated_image)

    def update(self):  # this function should only be run on the local player while in multiplayer mode, since it calls playerDied which triggers network events
        if self.health <= 0:
            if game.singleplayer and self == game.players[1]:
                game.playerDied(other=True)
            else:
                game.playerDied(other=False)
            return

        if self.reloadstate > settings['Game.FPS'].val * settings['Player.reload'].val * settings['Player.minreload'].val:
            self.reloadstate -= 1

        if self.bot is not None:
            actions = self.bot.step(self.game)
            if botlib.Action.THRUST in actions:
                self.thrust()
            if botlib.Action.SHOOT in actions:
                self.tryShoot()
            if botlib.Action.ROTATE_LEFT_FINE in actions:
                self.rotate(1, True)
            elif botlib.Action.ROTATE_RIGHT_FINE in actions:
                self.rotate(-1, True)
            elif botlib.Action.ROTATE_RIGHT in actions:
                self.rotate(-1, False)
            elif botlib.Action.ROTATE_LEFT in actions:
                self.rotate(1, False)

        separation = self.advance()

        if separation < ((self.spr.rect.width / 2) + (self.spr.rect.height / 2)) / 2:
            if game.singleplayer and self == game.players[1]:
                game.playerDied(other=True)
            else:
                game.playerDied(other=False)
            return

        if self.pos.x < settings['Player.visiblepx'].val - (SCREENSIZE[0] / 2):
            self.pos.x = (SCREENSIZE[0] / 2) - settings['Player.visiblepx'].val
            self.pos.y = -self.pos.y
        elif self.pos.x > (SCREENSIZE[0] / 2) - settings['Player.visiblepx'].val:
            self.pos.x = settings['Player.visiblepx'].val - (SCREENSIZE[0] / 2)
            self.pos.y = -self.pos.y

        if self.pos.y < settings['Player.visiblepx'].val - (SCREENSIZE[1] / 2):
            self.pos.y = (SCREENSIZE[1] / 2) - settings['Player.visiblepx'].val
            self.pos.x = -self.pos.x
        elif self.pos.y > (SCREENSIZE[1] / 2) - settings['Player.visiblepx'].val:
            self.pos.y = settings['Player.visiblepx'].val - (SCREENSIZE[1] / 2)
            self.pos.x = -self.pos.x

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
        self.players = []

        if not singleplayer:
            self.stopSendtoThread = False
            self.msgQueue = []  # apparently a regular list is thread-safe in python in 2022
            self.msgQueueEvent = threading.Event()
            threading.Thread(target=self.sendto).start()

        self.newRound()

    def playerDied(self, other=False, both=False, sendpacket=True):
        # other: did the other player die or did we die?
        global statusmessage

        self.state = GameState.DEAD

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
        self.framecounter = 0
        if len(self.players) > 0:
            self.players[0].reset()
            self.players[1].reset()

    def initPlayers(self):
        if len(self.players) > 0:
            print('Already initialized players')
            return

        self.players = [
            Player(1, self, bot=None),
            Player(2, self, bot='bots.random'),
        ]
        self.players[0].reset()
        self.players[1].reset()

    def connect(self, server):
        global statusmessage

        self.server = server
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(0)
        self.sock.sendto(mplib.clienthello, server)  # using sendtoQueued() here makes recvfrom() give an error on Windows
        self.state = GameState.HELLOSENT
        statusmessage = 'Waiting for server initial response...'

    def sendto(self):
        while True:
            if len(self.msgQueue) == 0:
                # Doing this thread blocking/unblocking is ~13× faster than starting a new thread for every packet
                self.msgQueueEvent.clear()
                # TODO sometimes it hangs here when you hit escape...
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
        # Send packet directly instead of waiting for the sendto() thread to do a loop until we can stop it cleanly
        self.sock.sendto(mplib.playerquits + reason.encode('ASCII'), self.server)
        self.stopSendtoThread = True
        self.msgQueueEvent.set()
        self.nextPingAt = None

    def processIncomingPacket(self, msg):
        global statusmessage

        if self.state == GameState.HELLOSENT:
            if msg[0 : len(mplib.serverhello)] != mplib.serverhello:
                statusmessage = 'Server protocol error, please restart the game.'
            else:
                mptoken = msg[len(mplib.serverhello) : ]
                self.sendtoQueued(mptoken)
                self.state = GameState.TOKENSENT
                statusmessage = 'Completing server handshake...'

                self.newRound()
                self.schedulePing()

                self.players[0].seqno += 1


        elif self.state == GameState.TOKENSENT:
            if msg == mplib.urplayerone:
                statusmessage = 'Server connection established. Waiting for another player to join this server...'
                self.players[0].n = 1
                self.players[1].n = 2
            elif msg == mplib.playerfound:
                self.state = GameState.MATCHED
                reply = mplib.settingsmsg + Setting.serializeSettings(settings)
                self.sock.sendto(reply, SERVER)
                self.sock.sendto(reply, ('127.0.0.1', self.sock.getsockname()[1]))  # also send it to ourselves
            elif msg == mplib.urplayertwo:
                statusmessage = 'Server found a match! Waiting for the other player to send game data...'
                self.players[0].n = 2
                self.players[1].n = 1
                self.state = GameState.MATCHED
            else:
                statusmessage = 'Server protocol error, please restart the game.'
                print('Got from server:', msg)

        elif self.state == GameState.MATCHED:
            if msg[ : len(mplib.settingsmsg)] != mplib.settingsmsg:
                print('Waiting for initial setup data, got this instead: ', msg)
                return

            # TODO this needs some way of resetting between rounds
            Setting.updateSettings(settings, msg[len(mplib.settingsmsg) : ])

            update_fps()

            gravitywell.setImage(settings['GW.imagenumber'].val)
            self.players[self.players[0].n - 1].pos = pygame.math.Vector2(settings['Player1.x'].val, settings['Player1.y'].val)
            self.players[self.players[0].n - 1].speed = pygame.math.Vector2(settings['Player1.xspeed'].val, settings['Player1.yspeed'].val)
            self.players[self.players[0].n - 1].mass = settings['Player.mass'].val
            self.players[self.players[1].n - 1].pos = pygame.math.Vector2(settings['Player2.x'].val, settings['Player2.y'].val)
            self.players[self.players[1].n - 1].speed = pygame.math.Vector2(settings['Player2.xspeed'].val, settings['Player2.yspeed'].val)
            self.players[self.players[1].n - 1].mass = settings['Player.mass'].val

            self.players[0].draw(screen)  # updates the sprite, which also does collision detection, to prevent collision on frame 0
            self.state = GameState.PLAYERING
            statusmessage = ''

        elif self.state in (GameState.PLAYERING, GameState.DEAD):
            if msg.startswith(mplib.playerquits):
                reason = msg[len(mplib.playerquits) : ]
                if reason == mplib.restartpl0x:
                    statusmessage += ' The other player restarted!'
                else:
                    if self.state == GameState.PLAYERING:
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
        self.nextPingAt = random.randint(int(settings['Game.FPS'].val * (prefs['Multiplayer.pinginterval'] / 2)), int(settings['Game.FPS'].val * (prefs['Multiplayer.pinginterval'] * 2)))
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
        # TODO IPv6..?
        hostOrIP, port = hostAndPort.split(':', 1)
        port = int(port)

    try:
        ip = socket.gethostbyname(hostOrIP)
    except Exception as e:
        print('Error looking up server name to get an IP, might you not have Internet or might the DNS server be down?')
        raise e

    return (ip, port)


def initSinglePlayer():
    game.players[0].pos = pygame.math.Vector2(settings['Player1.x'].val, settings['Player1.y'].val)
    game.players[0].speed = pygame.math.Vector2(settings['Player1.xspeed'].val, settings['Player1.yspeed'].val)
    game.players[0].mass = settings['Player.mass'].val
    game.players[0].draw(screen)  # updates the sprite position to avoid a collision with player 2
    game.players[1].pos = pygame.math.Vector2(settings['Player2.x'].val, settings['Player2.y'].val)
    game.players[1].speed = pygame.math.Vector2(settings['Player2.xspeed'].val, settings['Player2.yspeed'].val)
    game.players[1].mass = settings['Player.mass'].val
    game.players[1].draw(screen)
    game.newRound()
    game.state = GameState.PLAYERING
    gravitywell.setImage(settings['GW.imagenumber'].val)


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


SCREENSIZE = (1900, 980)

args = parseArgs(sys.argv)

# don't just pygame.init() because it will hang and not quit when you do pygame.quit();sys.exit();. Stackoverflow suggests in 2013 this was a Wheezy bug, but it works on a
# newer-than-Wheezy system, and then does not work on an even newer system than that, so... initializing only what we need is also literally 20 times faster (0.02 instead of 0.4 s)!
pygame.display.init()
pygame.font.init()
font_statusMsg = pygame.font.SysFont(None, 48)
fpslimiter = pygame.time.Clock()
screen = pygame.display.set_mode(SCREENSIZE)
statusmessage = ''

if not args['singleplayer']:
    # if dns lookup is needed, do this now (works also if you enter an IP, gethostbyname will just return it literally)
    # else sock.sendto() will do dns lookup for every call and, depending on the setup, that might hit the network for sending each individual update packet
    if args['server'] is not None:
        SERVER = prepareHostAndPort(args['server'])
    else:
        SERVER = prepareHostAndPort(prefs['Multiplayer.server'])

if not prefs['Game.simple_graphics'] and prefs['Game.backgroundimage'] is not None:
    bgimg = pygame.transform.scale(pygame.image.load(prefs['Game.backgroundimage']), SCREENSIZE).convert_alpha()

game = Game(singleplayer=args['singleplayer'])
game.initPlayers()
gravitywell = GravityWell()

if game.singleplayer:
    initSinglePlayer()
else:
    game.connect(SERVER)

update_fps()

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
        # 1px on either side for fuzzy/semi-transparent borders
        screen.blit(gravitywell.image, coordsToPx(-settings['GW.radius'].val - 1, -settings['GW.radius'].val - 1))
        gravitywell.animationStep()

    if game.state == GameState.PLAYERING:
        fineMode = keystates[pygame.K_LSHIFT] or keystates[pygame.K_RSHIFT]

        game.players[0].rotate(keystates[pygame.K_LEFT] - keystates[pygame.K_RIGHT], fineMode)

        if keystates[pygame.K_SPACE]:
            game.players[0].tryShoot()

        if keystates[pygame.K_UP]:
            game.players[0].thrust(fineMode)

        removebullets = []
        for bullet in game.bullets:
            died = bullet.advance(SCREENSIZE)
            if died:
                removebullets.append(bullet)
        for bullet in removebullets:
            game.bullets.remove(bullet)
        for player in game.players:
            removebullets = pygame.sprite.spritecollide(player.spr, game.bullets, False, pygame.sprite.collide_circle)
            for bullet in removebullets:
                game.sparks.append(Spark(bullet.pos))
                game.bullets.remove(bullet)
                # If we're in singleplayer, setting `player` health simply works as expected.
                # In multiplayer, we receive hit and health info from the other player so, in that case, alter the player health only if we hit ourselves (game.players[0])
                if game.singleplayer or player.n == game.players[0].n:
                    player.health = max(0, player.health - settings['Bullet.damage'].val)
                else:
                    game.players[0].hitsdealt += 1

        removesparks = []
        for spark in game.sparks:
            died = spark.advance(screen)
            if died:
                removesparks.append(spark)
            else:
                screen.blit(spark.img, coordsToPx(roundi(spark.pos.x), roundi(spark.pos.y)))
        for spark in removesparks:
            game.sparks.remove(spark)

        for bulletpos in game.remotebullets + [bullet.rect.center for bullet in game.bullets]:
            pygame.draw.circle(screen, prefs['Bullet.color'], coordsToPx(*bulletpos), settings['Bullet.size'].val)

        game.players[0].update()
        if game.singleplayer:
            game.players[1].update()

        for player in game.players:
            player.draw(screen)

            idis = player.rotatedMaxSize * prefs['Player.indicator_distance']
            iwidth = roundi(player.rotatedMaxSize * prefs['Player.indicator_width'])
            iheight = roundi(player.rotatedMaxSize * prefs['Player.indicator_height'])

            # Use int() for size calculations instead of roundi() because it'll do this "rounding towards the even choice" and you get it trying to draw on even coordinates of the screen (jumping around)
            # Draw battery level indicators
            bl = player.batterylevel / settings['Player.battSize'].val
            bgcol = prefs['Player.indicator_energy_color_bg']
            poweryellow = prefs['Player.indicator_energy_color_good']
            if player.batterylevel < (settings['Player.thrust'].val / settings['Player.thrust/kJ'].val):
                indicatorcolor = prefs['Player.indicator_energy_color_out']
            elif player.batterylevel < settings['Player.kJ/shot'].val:
                indicatorcolor = prefs['Player.indicator_energy_color_low']
            else:
                indicatorcolor = poweryellow
            x = int(player.pos.x - (iwidth / 2))
            y = int(player.pos.y + (player.rotatedMaxSize / 2) + idis)
            # outer rectangle
            pygame.draw.rect(screen, indicatorcolor, (*coordsToPx(x - 1, y + 1), int((iwidth + 2)),      int(iheight + 2)))
            # inner black area (same area as above but -1px on each side)
            pygame.draw.rect(screen, bgcol,          (*coordsToPx(x - 0, y + 2), int((iwidth + 0)),      int(iheight + 0)))
            # battery level (drawn over the black area)
            pygame.draw.rect(screen, poweryellow   , (*coordsToPx(x - 0, y + 2), int((iwidth + 0) * bl), int(iheight + 0)))

            # Draw health indicators
            healthgreen = prefs['Player.indicator_health_color_good']
            indicatorcolor = healthgreen if player.health > settings['Bullet.damage'].val else prefs['Player.indicator_health_color_low']
            bgcol = prefs['Player.indicator_health_color_bg']
            x = int(player.pos.x - (iwidth / 2))
            y = int(player.pos.y - (player.rotatedMaxSize / 2) - idis)
            # outer rectangle
            pygame.draw.rect(screen, indicatorcolor, (*coordsToPx(x - 1, y - 2), int((iwidth + 2)),                 int(iheight + 2)))
            # inner black area (same area as above but -1px on each side)
            pygame.draw.rect(screen, bgcol,          (*coordsToPx(x - 0, y - 1), int((iwidth + 0)),                 int(iheight + 0)))
            # health level (drawn over the black area)
            pygame.draw.rect(screen, healthgreen,    (*coordsToPx(x - 0, y - 1), int((iwidth + 0) * player.health), int(iheight + 0)))

        if prefs['Game.show_aim_guide']:
            b = Bullet(game.players[0], virtual=True)
            for i in range(int(prefs['Game.aim_guide_distance'] * settings['Game.FPS'].val / settings['Game.speed'].val)):
                oldpos = pygame.math.Vector2(b.pos)
                died = b.advance(SCREENSIZE)
                if died:
                    break
                pygame.draw.line(screen, prefs['Game.aim_guide_color'], coordsToPx(*oldpos), coordsToPx(*b.pos))


        game.sendUpdatePacket()
    elif game.state == GameState.DEAD:
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

    game.framecounter += 1

    pygame.display.flip()
    frametime = fpslimiter.tick(settings['Game.FPS'].val)
    if frametime * 0.9 > frame_time_budget * 1000:  # 10% margin because it will sleep longer sometimes to keep the fps *below* the target amount
        print('frametime was', frametime)

