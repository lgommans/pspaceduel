
'''
  Hello! This is your settings file speaking. Yes, I know. Please remain calm. You are OK.
  
  The game has three kinds of parameters:

    - User preferences: the variable 'prefs' below.
      Things like game colors can be modified freely.

    - Game settings: the variable 'settings' below.
      Things like bullet speed. These will be sent to the other player if you connect or restart before the other player does; otherwise, their settings will be sent to you.

    - Constants
      These affect gameplay and cannot be changed: you game would become incompatible. These cannot be found in this file.
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


prefs = {
    # Default server to connect to
    'Multiplayer.server': 'lucgommans.nl:9473',
    # Average seconds between determining the bidirectional connection latency. The actual value is chosen in the range (pinginterval÷2, pinginterval×2).
    # This is just an informational value that is printed to the console and actually includes frame time (=not very accurate).
    'Multiplayer.pinginterval': 4,

    # Use simpler, faster graphics (currently does not make a big difference)
    'Game.simple_graphics': False,

    # Show a prediction line for bullets
    'Game.show_aim_guide':  True,

    # Degrees you rotate per game step while holding down the left or right arrow key. Each degree requires a certain amount of energy so changing the value will not impact your energy consumption.
    'Player.rotate_speed':      4,  
    # Same, but while holding Shift + arrow left or right.
    'Player.rotate_speed_fine': 1,

    # How big/tall should the health and energy indicators be, as a fraction of the player height after scaling?
    'Player.indicator_height':   0.18,
    # How far away should these indicators be, as a fraction of the player height after scaling?
    'Player.indicator_distance': 0.6,

    # Number of frames for which a spark will exist, randomly chosen within this interval
    'Spark.lifespan': (4, 10),
    # Number of pixels it randomly moves per frame in each direction, randomly chosen within this interval. The direction (positive or negative) is a 50/50 chance.
    'Spark.movement': (1, 2),
    # The degrees it rotates per frame, randomly chosen within this interval. The direction (positive or negative rotation) is a 50/50 chance.
    'Spark.rotation': (2, 90),
    # The image used for sparks
    'Spark.graphic':  'res/venting.png',

    # Amount of red, green, and blue as a value from 0-255
    'Bullet.color':   (240, 120, 0),
}

# These settings are applied in single player and when you are the first player to arrive in a multiplayer game
settings = {
    # How much damage a single hit incurs
    'Bullet.damage':   Setting(  0.1, 'B', lambda n: int(round(n * 255)), lambda n: n / 255),
    # How heavy a bullet is (kilograms)
    'Bullet.mass':     Setting(  0.5, 'B', lambda n: int(round(n * 255)), lambda n: n / 255), 
    # Impulse with which the bullet is launched, either relative to the craft or relative to the star (see Bullet.relspeed)
    'Bullet.speed':    Setting(  5,   'B', lambda n: int(round(n * 10)),  lambda n: n / 10),
    # Should bullets fly with 'absolute' (relative to star) speed or with 'relative' (relative to the craft) speed?
    'Bullet.relspeed': Setting(False, 'B', lambda b: 1 if b else 0,       lambda b: True if b == 1 else False),
    # Size of the bullet, visually and collision-wise
    'Bullet.size':     Setting(  2,   'B', lambda n: int(round(n * 10)),  lambda n: int(round(n / 10))),

    # Size of the player as a fraction of the image in the resources folder
    'Player.scale':    Setting(  0.2, 'B', lambda n: int(round(n * 100)), lambda n: n / 100),
    # How much of the player sprite should still be visible before it wraps when hitting the screen's edge (pixels)
    'Player.visiblepx':Setting(  1,   'b'),
    # Start x and y, and initial speed, of player 1
    'Player1.x':       Setting(300,   'h'),
    'Player1.y':       Setting(300,   'h'),
    'Player1.xspeed':  Setting( -0.5, 'h', lambda n: int(round(n * 100)), lambda n: n / 100),
    'Player1.yspeed':  Setting(  0.5, 'h', lambda n: int(round(n * 100)), lambda n: n / 100),
    # Start x and y, and initial speed, of player 2
    'Player2.x':       Setting(900,   'h'),
    'Player2.y':       Setting(700,   'h'),
    'Player2.xspeed':  Setting(  0.5, 'h', lambda n: int(round(n * 100)), lambda n: n / 100),
    'Player2.yspeed':  Setting( -0.5, 'h', lambda n: int(round(n * 100)), lambda n: n / 100),
    # Size of the players' batteries (kilojoules)
    'Player.battSize': Setting(110,   'B'),
    # Strength of the players' engine (Newtons)
    # A real ion engine delivers more like 1 Newton on 5 kW, but we're also orbiting a star in seconds so we need some oomph in here
    'Player.thrust':   Setting(300,   'H'),
    # How many Newtons do we get out of a kJ from the battery?
    'Player.thrust/kJ':Setting(800,   'H'),
    # How many degrees of rotation do we get out of a kJ from the battery?
    'Player.rot/kJ':   Setting( 80,   'H'),
    # How many kJ does a single shot take?
    'Player.kJ/shot':  Setting( 12,   'B'),
    # Weight of the spacecraft (kilograms)
    'Player.mass':     Setting(100,   'B'),
    # Time required to reload the craft (seconds)
    'Player.reload':   Setting(  0.4, 'B', lambda n: int(round(n * 100)), lambda n: n / 100),
    # How much can the craft prepare a next shot to shoot faster bursts? Value multiplied with Player.reload, so -0.5 with Player.reload of 0.1 will be 'negative' 0.05 seconds reload state
    'Player.minreload':Setting(  0.0, 'b', lambda n: int(round(n * 100)), lambda n: n / 100),

    # Weight of the star (kilograms)
    'GW.mass':         Setting(4e14,  'H', lambda n: int(round(math.log(n, 1.1))), lambda n: pow(1.1, n)),
    # Maximum amount of radiative energy that can be picked up by the spacecraft per game step, considering its solar panel size and efficiency (kJ)
    'GW.radiation':    Setting( 10,   'B'),
}

