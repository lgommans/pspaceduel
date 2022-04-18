
'''
  Hello! This is your settings file speaking. Yes, I know. Please remain calm. You are OK.
  
  This file contains two kinds of parameters:

    - User preferences: the 'prefs' list below.
      Things like game colors can be modified freely.

    - Game settings: the 'settings' list below.
      Things like bullet speed. These will be sent to the other player if you connect or restart before the other player does; otherwise, their game settings will be sent to you.

  Color values are given in «(Red, Green, Blue)» with amounts for each ranging from 0-255.
  Toggle settings are specified as «True» or «False».
  Numbers can have different valid ranges, but anything sensible should be supported.
  Coordinates are given in «(x, y)». Player positions are relative to the gravity well at the center of the screen, so «(-100, 0)» will appear just left of the center.
  File names have to be between apostrophes or quotes: «"some_background_image.png"»

'''

import math, struct

class Setting:
    def getStructFormat(settings):
        # We might not need this sorting since `dict` is now ordered (Py3.7), but I like the mydict={data} syntax better than doing explicit
        # inserts and it doesn't say order is still guaranteed with this syntax. And this way we get to have compat with older pythons.

        structformat = ''
        for key in sorted(settings.keys()):  # yes, we could do a [list_comprehension].join(''), but this is way more readable imo
            structformat += settings[key].structtype
        return structformat


    def serializeSettings(settings):
        values = []
        for key in sorted(settings.keys()):
            values.append(settings[key].serialize())

        return struct.pack(Setting.getStructFormat(settings), *values)


    def updateSettings(settings, serializedSettings):  # updates the `settings` argument in-place
        rawvalues = struct.unpack(Setting.getStructFormat(settings), serializedSettings)
        for i, key in enumerate(sorted(settings.keys())):
            settings[key].val = settings[key].deserialize(rawvalues[i])


    def __init__(self, value, structtype, serialize=None, deserialize=None):
        self.structtype = structtype
        self.val = value
        if serialize is not None:
            self.serialize = lambda: serialize(self.val)
        else:
            self.serialize = lambda: self.val

        if serialize is not None:
            self.deserialize = lambda v: deserialize(v)
        else:
            self.deserialize = lambda v: v


###
# User preferences. Change these however you like :)
###
prefs = {
    # Default server to connect to
    'Multiplayer.server': 'lucgommans.nl:9473',
    # Average seconds between determining the bidirectional connection latency. The actual value is chosen in the range (pinginterval÷2, pinginterval×2).
    # This is just an informational value that is printed to the console and includes frame time (=not very accurate).
    'Multiplayer.pinginterval': 4,

    # Use simpler, faster graphics (currently does not make a big difference)
    'Game.simple_graphics': False,
    # The base image that goes behind everything else. Set to None for, well, none
    'Game.backgroundimage': 'res/Messier-101-test.jpg',
    # Color and position of the main text messages
    'Game.text_color':      (  0, 90, 224),
    'Game.text_position':   (10, 50),

    # Show a prediction line for bullets
    'Game.show_aim_guide':  True,
    # The color of the line
    'Game.aim_guide_color': ( 80, 190,  20),
    # How long should the aim guide be? Measured in seconds, i.e. how far a bullet flies in 2 seconds (you might liken it to the 'light year' distance unit!)
    'Game.aim_guide_distance': 2,

    # Degrees you rotate per game step while holding down the left or right arrow key. Each degree requires a certain amount of energy so changing the value will not impact your energy consumption.
    'Player.rotate_speed':      4,  
    # Same, but while holding Shift + arrow left or right.
    'Player.rotate_speed_fine': 1,

    # Maximum engine thrust is a game setting, not a user preference, but with the Shift key you can do a more minor adjustment. How much should that factor be?
    'Player.thrust_factor_fine': 0.3,

    # How big/tall should the health and energy indicators be, as a fraction of the player height after scaling?
    'Player.indicator_height':   0.14,
    # How far away should these indicators be, as a fraction of the player height after scaling?
    'Player.indicator_distance': 0.5,
    # Colors of your health bar (green by default, orange if the next bullet would kill you)
    'Player.indicator_health_color_good': ( 10, 230,  10),
    'Player.indicator_health_color_low':  (255, 100,   0),
    'Player.indicator_health_color_bg':   (  0,   0,   0),
    # Colors of your energy bar (yellow by default, orange if you can't shoot, red if you can't meaningfully use your engine anymore)
    'Player.indicator_energy_color_good': (255, 200,   0),
    'Player.indicator_energy_color_low':  (255, 128,   0),
    'Player.indicator_energy_color_out':  (255,   0,   0),
    'Player.indicator_energy_color_bg':   (  0,   0,   0),

    # Number of frames for which a spark will exist, randomly chosen within this interval
    'Spark.lifespan': (5, 11),
    # Number of pixels it randomly moves per frame in each direction, randomly chosen within this interval. The direction (positive or negative) is a 50/50 chance.
    'Spark.movement': (1, 2),
    # The degrees it rotates per frame, randomly chosen within this interval. The direction (positive or negative rotation) is a 50/50 chance.
    'Spark.rotation': (2, 90),
    # The image used for sparks
    'Spark.graphic':  'res/venting.png',

    # The color of the spheres you shoot
    'Bullet.color':   (255, 180,  20),
}

###
# Game settings.
# These are synchronised with the other player when you are the first player to arrive in a multiplayer game, or when you play singleplayer.
# If you change anything aside from the value, e.g. the 'B' or 'h' or 'lambda' field, your game will be incompatible with other players who did not make the exact same change!
# TODO explain how to change the setting and to leave the lambda etc. alone
###
settings = {
    # How fast the game runs (how much time is simulated every frame)
    'Game.speed':      Setting(   0.3, 'H', lambda n: int(round(n * 255)), lambda n: n / 255),

    # How much damage a single hit incurs
    'Bullet.damage':   Setting(   0.1, 'B', lambda n: int(round(n * 255)), lambda n: n / 255),
    # How heavy a bullet is (kilograms)
    'Bullet.mass':     Setting(   0.5, 'B', lambda n: int(round(n * 255)), lambda n: n / 255), 
    # Impulse with which the bullet is launched, either relative to the craft or relative to the star (see Bullet.relspeed)
    'Bullet.speed':    Setting(   5,   'B', lambda n: int(round(n * 10)),  lambda n: n / 10),
    # Should bullets fly with 'absolute' (relative to star) speed or with 'relative' (relative to the craft) speed?
    'Bullet.relspeed': Setting( True,  'B', lambda b: 1 if b else 0,       lambda b: True if b == 1 else False),
    # Size of the bullet, visually and collision-wise
    'Bullet.size':     Setting(   2,   'B', lambda n: int(round(n * 10)),  lambda n: int(round(n / 10))),

    # Size of the player as a fraction of the image in the resources folder
    'Player.scale':    Setting(   0.07,'B', lambda n: int(round(n * 200)), lambda n: n / 200),
    # How much of the player sprite should still be visible before it wraps when hitting the screen's edge (pixels)
    'Player.visiblepx':Setting(   2,   'b'),
    # Start x and y, and initial speed, of player 1
    'Player1.x':       Setting(-300,   'h'),
    'Player1.y':       Setting(   0,   'h'),
    'Player1.xspeed':  Setting(   0,   'h', lambda n: int(round(n * 100)), lambda n: n / 100),
    'Player1.yspeed':  Setting( 2.5,   'h', lambda n: int(round(n * 100)), lambda n: n / 100),
    # Start x and y, and initial speed, of player 2
    'Player2.x':       Setting( 300,   'h'),
    'Player2.y':       Setting(   0,   'h'),
    'Player2.xspeed':  Setting(   0,   'h', lambda n: int(round(n * 100)), lambda n: n / 100),
    'Player2.yspeed':  Setting(-2.5,   'h', lambda n: int(round(n * 100)), lambda n: n / 100),
    # Battery capacity for each player (kilojoules)
    'Player.battSize': Setting( 180,   'H'),
    # Strength of the players' engine (Newtons)
    # A real ion engine delivers more like 1 Newton on 5 kW, but we're also orbiting a star in seconds instead of years so we need a bit more oomph here
    'Player.thrust':   Setting( 200,   'H'),
    # How many Newtons do we get out of a kJ from the battery?
    'Player.thrust/kJ':Setting( 600,   'H'),
    # How many degrees of rotation do we get out of a kJ from the battery?
    'Player.rot/kJ':   Setting(  80,   'H'),
    # How many kJ does a single shot take?
    'Player.kJ/shot':  Setting(  12,   'B'),
    # Weight of the spacecraft (kilograms)
    'Player.mass':     Setting( 100,   'B'),
    # Time required to reload the craft (seconds)
    'Player.reload':   Setting(   0.4, 'B', lambda n: int(round(n * 100)), lambda n: n / 100),
    # How much can the craft prepare a next shot to shoot faster bursts? Value multiplied with Player.reload, so -0.5 with Player.reload of 0.1 will be 'negative' 0.05 seconds reload state
    'Player.minreload':Setting(   0.0, 'b', lambda n: int(round(n * 100)), lambda n: n / 100),

    # The Gravity Well (GW) is the heavy object in the middle. Here you can configure whether it appears as a star (such as the Sun) or a planet or so.
    'GW.imagenumber':  Setting(   4,   'B'),
    # Weight of the GW (kilograms)
    'GW.mass':         Setting(2e15,   'H', lambda n: int(round(math.log(n, 1.1))), lambda n: pow(1.1, n)),
    # Maximum amount of radiative energy that can be picked up by the spacecraft per game step, considering its solar panel size and efficiency (kJ)
    'GW.radiation':    Setting(  10,   'B'),
    # Half of the diameter of the GW in pixels (it is always perfectly spherical even if its image can have protrusions)
    'GW.radius':       Setting(  60,   'B', lambda n: int(round(n * 2)), lambda n: n / 2),
}

