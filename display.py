import pygame
from pygame import HWSURFACE, DOUBLEBUF

SIZE = [10, 10]
SCR_SIZE = [64, 32]
COLORS = {
  0: (  0,   0,   0),
  1: (255, 255, 255),
}

class display(object):
    def __init__(self):
        self.set_pixel_size(*SIZE)
        self.set_screen_size(*SCR_SIZE)
        self.set_title()
    
    def set_title(self, title=None):
        if title:
            pygame.display.set_caption("{} - CHIP-8".format(title))
        else:
            pygame.display.set_caption("CHIP-8")
    
    def get_pixel(self, x, y):
        return self.gfx[y][x]
    
    def set_pixel(self, x, y, pixel):
        pixel = int(pixel)
        self.gfx[y][x] = pixel
        rect  = self.get_pixel_rect(x, y)
        pygame.draw.rect(self.screen, COLORS[pixel], rect)
    
    def get_screen_size(self):
        return self.scr_size
    
    def set_screen_size(self, x, y):
        self.gfx = []
        for iy in xrange(y):
            self.gfx.append([0] * x)
        self.scr_size = [x, y]
        self.fscr_size = [self.psize[0] * x,
                          self.psize[1] * y]
        self.screen = pygame.display.set_mode(self.fscr_size,
                                              HWSURFACE|DOUBLEBUF,
                                              8)
    
    def get_pixel_size(self):
        return self.psize
    
    def set_pixel_size(self, x, y):
        self.psize = [x, y]
    
    def get_pixel_rect(self, x, y):
        sx, sy = self.get_pixel_size()
        rect = [x * sx, y * sy, sx, sy]
        return rect
    
    def update(self):
        pygame.display.flip()
        return
        sx, sy = self.get_screen_size()
        #self.screen.fill(COLORS[0])
        for y in xrange(sy):
            for x in xrange(sx):
                rect  = self.get_pixel_rect(x, y)
                pixel = self.get_pixel(x, y)
                pygame.draw.rect(self.screen, COLORS[pixel], rect)
        pygame.display.flip()
