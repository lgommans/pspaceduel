
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
    'Player.thrust':   Setting(300,   'H'),
    # How many Newtons do we get out of a kJ from the battery?
    'Player.thrust/kJ':Setting(800,   'H'),
    # How many degrees of rotation do we get out of a kJ from the battery?
    'Player.rot/kJ':   Setting( 80,   'H'),
    # How many kJ does a single shot take?
    'Player.kJ/shot':  Setting( 12,   'B'),
    # Weight of the spacecraft (kilograms)
    'Player.mass':     Setting(100,   'B'),
    # Weight of the star (kilograms)
    'GW.mass':         Setting(4e14,  'H', lambda n: int(round(math.log(n, 1.1))), lambda n: pow(1.1, n)),
    # Maximum amount of radiative energy that can be picked up by the spacecraft per game step, considering its solar panel size and efficiency (kJ)
    'GW.radiation':    Setting( 10,   'B'),
}

