import struct

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

