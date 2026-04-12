+-=-=-=-=-=-=-=-=-=-=-=-=-=-+
|                           |
|   P  S p a c e  D u e l   |
|                           |
+-=-=-=-=-=-=-=-=-=-=-=-=-=-+

In PSpaceDuel, two ships battle for dominance of a star system.

Your craft orbits a star. There is a pesky other craft that, if conveniently
removed, would grant you sole governance of the whole system! Why don't you
poke a few holes in those air tanks to get the message across?

The game uses real physics principles (e.g. gravity and radiative energy
calculations) where this is possible without compromising on gameplay.

All systems on board are, for all intents and purposes, electrical: an ion
drive (propulsion), mass driver (gun), and a reaction wheel (rotation).
Proximity to the star lets your solar panel harvest more energy.

Inspired by KSpaceDuel <https://apps.kde.org/kspaceduel/>
by Andreas Zehender (1998), this remake features:

- Online multiplayer
- Player settings are synchronised (based on who connects first), you do not
  have to join a specific server to play a certain configuration
- Good hitbox accuracy -- no more unexpected deaths 10km away from the star!
- Health and energy levels visualized near the player rather than having to
  look over at a control panel
- Written in Python instead of C
- No artificial limit to how many bullets are on the screen
- No pause button. No mom, I cannot pause this multiplayer game! :D

There are also regressions:

- No pause button. No mom, I cannot pause this multiplayer game! :(
- Hot seat multiplayer (players sharing a keyboard) is not supported
  (Heck, my keyboard doesn't support all combos of 3 concurrent keys, let alone
   those required for another player! PS/2 lent itself better for hot seat...)
- Powerups are not featured in this version
- Mines are not featured in this version

And lastly, a design change:

- Bullets do not wrap like players.
  I'd like the players to also not wrap for realism, but it increases the
  difficulty significantly: since solar panels barely work away from the star,
  one quite easily drifts off into space on an uncontrollable escape trajectory.
 

+-=-=-=-=-=-=-=-=-=-=-=-=-=-+
|                           |
|   G e t   P l a y i n g   |
|                           |
+-=-=-=-=-=-=-=-=-=-=-=-=-=-+

Install python3 and pygame for your platform.
Optionally install Pillow for loading animated GIFs used in some themes:
  `pip3 install pillow` or `apt install python3-pil`

You can now run the game. By default, it starts in multiplayer and waits
for a second player to join, but you can also run it in singleplayer mode:

  python3 client.py
  python3 client.py --singleplayer

Use --help to learn of other launch options.

Game controls:

  Arrow keys
  Shift + arrow keys to make finer adjustments
  Space to shoot

To run your own server:

  python3 server.py
  python3 client.py localhost


+-=-=-=-=-=-=-=-=-=-+
|                   |
|   L i c e n s e   |
|                   |
+-=-=-=-=-=-=-=-=-=-+

To be determined.
(No part of the original game was used, so we are free in choosing one.)

If you would like to make a derivative work or reuse some resource or part,
ping me so that I pick a license. It will be something like GPL, BSD, MIT, ...

The primary repository for this project is:
https://codeberg.org/lucg/pspaceduel

A mirror is available here:
https://github.com/lgommans/pspaceduel

