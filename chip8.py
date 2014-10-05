import pygame
import random

SIZE = [10, 10]
chip8_fontset = [
  0xF0, 0x90, 0x90, 0x90, 0xF0, # 0
  0x20, 0x60, 0x20, 0x20, 0x70, # 1
  0xF0, 0x10, 0xF0, 0x80, 0xF0, # 2
  0xF0, 0x10, 0xF0, 0x10, 0xF0, # 3
  0x90, 0x90, 0xF0, 0x10, 0x10, # 4
  0xF0, 0x80, 0xF0, 0x10, 0xF0, # 5
  0xF0, 0x80, 0xF0, 0x90, 0xF0, # 6
  0xF0, 0x10, 0x20, 0x40, 0x40, # 7
  0xF0, 0x90, 0xF0, 0x90, 0xF0, # 8
  0xF0, 0x90, 0xF0, 0x10, 0xF0, # 9
  0xF0, 0x90, 0xF0, 0x90, 0x90, # A
  0xE0, 0x90, 0xE0, 0x90, 0xE0, # B
  0xF0, 0x80, 0x80, 0x80, 0xF0, # C
  0xE0, 0x90, 0x90, 0x90, 0xE0, # D
  0xF0, 0x80, 0xF0, 0x80, 0xF0, # E
  0xF0, 0x80, 0xF0, 0x80, 0x80  # F
]

def chunks(l, n):
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

class display(object):
    def __init__(self):
        self.screen = pygame.display.set_mode((SIZE[0] * 64, SIZE[1] * 32))
        pygame.display.set_caption("chip-8")
    
    def draw(self, pixels):
        self.screen.fill((0, 0, 0))
        for y, row in enumerate(chunks(pixels, 64)):
            for x, pixel in enumerate(row):
                if pixel:
                    rect = [x * SIZE[0], y * SIZE[1]] + SIZE
                    pygame.draw.rect(self.screen, (255, 255, 255), rect)
        pygame.display.update()

class chip8(object):
    """
    CHIP-8 Emulator
    
        opcode - current instruction
        memory - 4K memory:
            0x000 - 0x1FF --- Reserved for the interpreter
            0x050 - 0x0A0 --- Built in 4x5 font set (0 - F)
            0x200 - 0xFFF --- Program ROM and work RAM
        
        Vx     - 15 registers from V0 to VE, 16th is for carry flag
        index  - index
        pc     - program counter
        
        gfx    - pixel array
        keys   - keys' states
        
        delay_timer - delay timer
        sound_timer - sound timer. Plays a beep when it hits 0
        
        stack  - jump stack
    """
    
    def _0ZZZ(self):
        opcode = self.opcode & 0xF0FF
        if opcode in self.funcmap0:
            self.funcmap0[opcode]()
        else:
            print "Unknown opcode: 0x%X" % self.opcode
    
    def _0NNN(self):
        # Ignored
        pass
    
    def _00E0(self):
        self.gfx = [0] * 64 * 32
        self.draw_flag = True
    
    def _00EE(self):
        self.pc = self.stack.pop()
    
    def _1NNN(self):
        self.pc = self.addr
    
    def _2NNN(self):
        self.stack.append(self.pc)
        self.pc = self.addr
        
    def _3XNN(self):
        if self.V[self.x] == self.nn:
            self.pc += 2
        
    def _4XNN(self):
        if self.V[self.x] != self.nn:
            self.pc += 2
        
    def _5XY0(self):
        if self.V[self.x] == self.V[self.y]:
            self.pc += 2
    
    def _6XNN(self):
        self.V[self.x] = self.nn
    
    def _7XNN(self):
        self.V[self.x] += self.nn
    
    def _8XYZ(self):
        opcode = self.opcode & 0xF00F
        if opcode in self.funcmap8:
            self.funcmap8[opcode]()
        else:
            print "Unknown opcode: 0x%X" % self.opcode
    
    def _8XY0(self):
        self.V[self.x] = self.V[self.y]
    
    def _8XY1(self):
        self.V[self.x] |= self.V[self.y]
    
    def _8XY2(self):
        self.V[self.x] &= self.V[self.y]
    
    def _8XY3(self):
        self.V[self.x] ^= self.V[self.y]
    
    def _8XY4(self):
        if self.V[self.x] + self.V[self.y] > 0xFF:
            self.V[0xF] = 1
        else:
            self.V[0xF] = 0
        self.V[self.x] += self.V[self.y]
    
    def _8XY5(self):
        if self.V[self.x] > self.V[self.y]:
            self.V[0xF] = 1
        else:
            self.V[0xF] = 0
        self.V[self.x] -= self.V[self.y]
    
    def _ANNN(self):
        self.index = self.opcode & 0x0FFF
    
    def _BNNN(self):
        self.pc = self.addr + self.V[0x0]
    
    def _CXNN(self):
        r = int(random.random() * 0xFF)
        self.V[self.x] = r & self.nn
        self.V[self.x] &= 0xFF
    
    def _DXYN(self):
        self.V[0xF] = 0
        x = self.V[self.x]
        y = self.V[self.y]
        height = self.opcode & 0x000F
        for row in xrange(height):
            crow = self.memory[self.index + row]
            for poffset in xrange(9):
                if (crow & (0x80 >> poffset)) != 0:
                    lx  = x + poffset
                    ly  = y + row
                    ly %= 32
                    lx %= 64
                    loc = lx + ly * 64
                    if self.gfx[loc] == 1:
                        self.V[0xF] = 1
                    self.gfx[loc] ^= 1
        self.draw_flag = True
        
    def _2DXYN(self):
        x = self.V[self.x]
        y = self.V[self.y]
        h = self.opcode & 0x000F
        self.V[0xF] = 0
        for y_index in xrange(h):
            pixel = self.memory[self.index + y_index]
            for x_index in xrange(8):
                if (pixel & (0x80 >> x_index)) != 0:
                    pos = (x + x_index + ((y + y_index) * 64))
                    print pos
                    if self.gfx[pos] == 1:
                        self.V[0xF] = 1
                    self.gfx[pos] ^= 1
        self.draw_flag = True
    
    def _EXZZ(self):
        opcode = self.opcode & 0xF0FF
        if opcode in self.funcmapE:
            self.funcmapE[opcode]()
        else:
            print "Unknown opcode: 0x%X" % self.opcode
    
    def _EX9E(self):
        if self.keys[self.V[self.x]] == 1:
            self.pc += 2
    
    def _EXA1(self):
        if self.keys[self.V[self.x]] == 0:
            self.pc += 2
    
    def _FXZZ(self):
        opcode = self.opcode & 0xF0FF
        if opcode in self.funcmapF:
            self.funcmapF[opcode]()
        else:
            print "Unknown opcode: 0x%X" % self.opcode
    
    def _FX07(self):
        self.V[self.x] = self.delay_timer
    
    def _FX15(self):
        self.delay_timer = 0#self.V[self.x]
        print self.delay_timer
    
    def _FX18(self):
        self.sound_timer = self.V[self.x]
    
    def _FX1E(self):
        self.index += self.V[self.x]
        if self.index >= 0xFFF:
            self.index &= 0xFFF
            self.V[0xF] = 1
        else:
            self.V[0xF] = 0
    
    def _FX29(self):
        self.index = (self.V[self.x] * 5) & 0xFFF
    
    def _FX33(self):
        vx = self.V[self.x]
        self.memory[self.index] = vx / 100
        self.memory[self.index + 1] = (vx % 100) / 10
        self.memory[self.index + 2] = vx % 10
    
    def _FX65(self):
        for i in xrange(self.V[self.x] + 1):
            self.V[i] = self.memory[self.index + i]
        self.index += self.V[self.x] + 1
    
    def initialize(self):
        """ See main docstring for info
        """
        self.opcode = 0
        self.memory = [0] * 4096
        
        self.V = [0] * 16
        self.index = 0
        self.pc    = 0x200 # 512
        
        self.gfx = [0] * 64 * 32
        self.keys = [0] * 16
        
        self.delay_timer = 0
        self.sound_timer = 0
        
        self.stack = [0] * 16
        self.running = True
        self.draw_flag = False
        
        for i in xrange(80):
            self.memory[i] = chip8_fontset[i]
        
        self.funcmap = {
            0x0000: self._0ZZZ,
            0x1000: self._1NNN,
            0x2000: self._2NNN,
            0x3000: self._3XNN,
            0x4000: self._4XNN,
            0x5000: self._5XY0,
            0x6000: self._6XNN,
            0x7000: self._7XNN,
            0x8000: self._8XYZ,
            0xA000: self._ANNN,
            0xB000: self._BNNN,
            0xC000: self._CXNN,
            0xD000: self._DXYN,
            0xE000: self._EXZZ,
            0xF000: self._FXZZ,
        }
        
        self.funcmap0 = {
            0x0000: self._0NNN,
            0x00E0: self._00E0,
            0x00EE: self._00EE,
        }
        
        self.funcmap8 = {
            0x8000: self._8XY0,
            0x8001: self._8XY1,
            0x8002: self._8XY2,
            0x8003: self._8XY3,
            0x8004: self._8XY4,
            0x8005: self._8XY5,
        }
        
        self.funcmapE = {
            0xE09E: self._EX9E,
            0xE0A1: self._EXA1,
        }
        
        self.funcmapF = {
            0xF007: self._FX07,
            0xF015: self._FX15,
            0xF018: self._FX18,
            0xF01E: self._FX1E,
            0xF029: self._FX29,
            0xF033: self._FX33,
            0xF065: self._FX65,
        }
    
    def beep(self):
        print "BEEP!"
    
    def load(self, name):
        data = open(name, "rb").read()
        for i in xrange(len(data)):
            self.memory[i + 0x200] = ord(data[i])
    
    def cycle(self):
        self.opcode = self.memory[self.pc] << 8 | self.memory[self.pc + 1]
        inst = self.opcode & 0xF000
        
        self.x = ((self.opcode & 0x0F00) >> 8)
        self.y = ((self.opcode & 0x00F0) >> 4)
        self.addr = self.opcode & 0x0FFF
        self.nn = self.opcode & 0x00FF
        
        if inst in self.funcmap:
            self.funcmap[inst]()
        else:
            print ("Unknown opcode: 0x%X" % self.opcode)
        self.pc += 2
        
        if self.delay_timer > 0:
            self.delay_timer -= 1
            if self.delay_timer == 0:
                print "0"
        #print self.delay_timer
        
        if self.sound_timer > 0:
            self.sound_timer -= 1
            if self.sound_timer == 0:
                self.beep()
    
    def draw(self):
        self.display.draw(self.gfx)
        self.draw_flag = False
    
    def main(self):
        self.initialize()
        self.load("PONG")
        self.display = display()
        clock = pygame.time.Clock()
        while self.running:
            self.cycle()
            
            if self.draw_flag:
                self.draw()
            clock.tick(60)

chip8().main()
