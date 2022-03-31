+-=-=-=-=-=-=-=-=-=-=-=-=-=-+
|                           |
|   P  S p a c e  D u e l   |
|                           |
+-=-=-=-=-=-=-=-=-=-=-=-=-=-+

In PSpaceDuel two ships battle for dominance of a star system.

Your craft orbits a star. There is a pesky other craft that, if conveniently
removed, would grant you sole governance of the whole system! Why don't you
poke a few holes in those air tanks to get the message across?

All systems on board are, for all intents and purposes, electrical: an ion
drive (propulsion), mass driver (gun), and a reaction wheel (rotation).
Proximity to the star lets your solar panel harvest more energy.

The game uses real physics principles (e.g. gravity and radiative energy
calculations) where this is possible without compromising gameplay.

Inspired by KSpaceDuel[1] by Andreas Zehender (1998), this remake features:

 - Online multiplayer
 - Player settings are synchronised (based on who connects first), you do not
   have to join a specific server to play a certain configuration 
 - Good hitbox accuracy -- no more unexpected deaths 10km away from the star!
 - Health and energy levels visualized near the player rather than having to
   look over at a control panel
 - Written in a more accessible language than low-level C
 - No artificial limit to how many bullets are on the screen
 - No pause button. No mom, I cannot pause this multiplayer game! :D

There are also regressions:

 - No pause button. No mom, I cannot pause this multiplayer game! :(
 - There is no AI (computer player)
 - Hot seat multiplayer (players sharing a keyboard) is not supported
   (Heck, I have a keyboard that doesn't support 3 concurrent keys, let alone
	those required for another player! PS/2 lent itself better for hot seat...)
 - Powerups are not featured in this version
 - Mines are not featured in this version
 - The code is a mess. I wanted to get it playable and a lot of technical debt
   was incurred along the way

And general changes:

- Bullets do not wrap like players.
  I'd like the players to also not wrap for realism, but it increases the
  difficulty significantly since solar panels barely work away from the star.
 
[1] https://apps.kde.org/kspaceduel/


+-=-=-=-=-=-=-=-=-=-=-=-=-=-+
|                           |
|   G e t   P l a y i n g   |
|                           |
+-=-=-=-=-=-=-=-=-=-=-=-=-=-+

Install python3 and pygame for your platform.

You can run a dummy singleplayer game (you can control only one craft)
by setting SINGLEPLAYER = True

For multiplayer:

 - There might be a server running on lucgommans.nl:9473
 - Else you can start a server using:  python3 server.py
   The game requires only UDP port 9473 (by default)

Run the client:  python3 client.py

Controls:

  Arrow keys
  Shift + arrow keys to rotate slower (more accuracy)
  Space to shoot


+-=-=-=-=-=-=-=-=-=-+
|                   |
|   L i c e n s e   |
|                   |
+-=-=-=-=-=-=-=-=-=-+

No part of the original game was used.

I still have to pick an open source license. If you would like to make a
derivative work or reuse some resource or part, ping me so that I pick a
license. It will be something like GPL, BSD, MIT, ...

