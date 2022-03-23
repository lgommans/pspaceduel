
maximumsize = 1400
clienthello = b'Many greetings oh glorious serverlord. I can haz token from your most gracious serveriness?'
serverhello = b'K. '
protocolerr = b':('
urplayerone = b"1"
urplayertwo = b"2"
playerfound = b'Player 2 found!'
playerquits = b'I take my leave since '
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
- ushort gravity well mass as a power to 1.1
'''
configstruct = '>BhhhhhhhhHHH'

'''
- short player x
- short player y
- short player xspeed in hundredths
- short player yspeed in hundredths
- ubyte player angle/1.5
'''
updatestruct = '>hhhhB'

