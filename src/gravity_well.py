import pygame
from settings import settings, prefs

imported_PIL = False

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
            elif imagenumber == 4:
                self.image = pygame.image.load("res/that's-no-moon.png").convert_alpha()
                self.frames = None
            else:
                print('Note: GravityWell image number', imagenumber, 'was requested but we do not have it.')

            self.framecounter = 0
            # 1px on either side for fuzzy/semi-transparent borders
            GWwidth = int(round((settings['GW.radius'].val + 1) * 2))
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



