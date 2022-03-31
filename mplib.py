
import struct

maximumsize = 1400
clienthello = b'Many greetings oh glorious serverlord. I can haz token from your most gracious serveriness?'
serverhello = b'K. '
protocolerr = b':('
urplayerone = b"1"
urplayertwo = b"2"
playerfound = b'Player 2 found!'
playerquits = b'I take my leave since '
restartpl0x = b'I would like to play another round on this server!'
playerlimit = b'FULL'

'''
- ubyte  version
- short  player 1 x
- short  player 1 y
- short  player 1 xspeed in hundredths
- short  player 1 yspeed in hundredths
- short  player 2 x
- short  player 2 y
- short  player 2 xspeed in hundredths
- short  player 2 yspeed in hundredths
- ushort battery capacity
- ushort engine thrust
- ushort thrust per kJ
- ushort gravity well mass as a power to 1.1
- ubyte  gravity well radiation energy
- ubyte  bullet damage
- ubyte  shoot kJ
'''
configstruct = struct.Struct('>BhhhhhhhhHHHHBBB')

'''
- uint   sequence number
- short player x
- short player y
- short player xspeed in hundredths  TODO is x/yspeed still needed?
- short player yspeed in hundredths
- ubyte player angle/1.5
- ubyte player battery level where 255 is max capacity
- ubyte player health times 255
- ubyte hits taken from the remote player's bullets
optionally followed by one or more bulletstructs
'''
updatestruct = struct.Struct('>IhhhhBBBB')

''' x, y '''
bulletstruct = struct.Struct('>hh')

