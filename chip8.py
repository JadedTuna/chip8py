# CHIP-8 emulator
# 
# Working ROMs:
# BRIX (?)
# MAZE
# MERLIN (?)
# PONG
# PONG2
# PUZZLE (?)
# TETRIS
# VBRIX (??)
# VERS (?)
# WIPEOFF
# 

import pygame
import random
import socket, thread # For remote hex keyboard
import argparse
import traceback
from display import display
pygame.init()

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
KEYMAP = {
  pygame.K_1: 0,
  pygame.K_2: 1,
  pygame.K_3: 2,
  pygame.K_4: 3,
  
  pygame.K_q: 4,
  pygame.K_w: 5,
  pygame.K_e: 6,
  pygame.K_r: 7,
  
  pygame.K_a: 8,
  pygame.K_s: 9,
  pygame.K_d: 10,
  pygame.K_f: 11,
  
  pygame.K_z: 12,
  pygame.K_x: 13,
  pygame.K_c: 14,
  pygame.K_v: 15,
}
RKEYMAP = {
    "17": (0, 1),
    "1":  (0, 0),
    
    "18": (1, 1),
    "2":  (1, 0),
    
    "19": (2, 1),
    "3":  (2, 0),
    
    "28": (3, 1),
    "12": (3, 0),
    
    
    "20": (4, 1),
    "4":  (4, 0),
    
    "21": (5, 1),
    "5":  (5, 0),
    
    "22": (6, 1),
    "6":  (6, 0),
    
    "29": (7, 1),
    "13": (7, 0),
    
    
    "23": (8, 1),
    "7":  (8, 0),
    
    "24": (9, 1),
    "8":  (9, 0),
    
    "25": (10, 1),
    "9":  (10, 0),
    
    "30": (11, 1),
    "14": (11, 0),
    
    
    "26": (12, 1),
    "10": (12, 0),
    
    "16": (13, 1),
    "0":  (13, 0),
    
    "27": (14, 1),
    "11": (14, 0),
    
    "31": (15, 1),
    "15": (15, 0),
}

def chunks(l, n):
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

class remotekbd(object):
    def __init__(self, cpu):
        self.cpu = cpu
        self.sock = socket.socket()
        thread.start_new(self.listen, ())
    
    def _listen(self):
        try:
            self.listen()
        except:
            pass
        self.sock.close()
    
    def listen(self):
        try:
            self.sock.bind(("0.0.0.0", 0x123C))
            print "Remote keyboard started"
        except socket.error:
            print "Failed to start remote keyboard"
            return
        self.sock.listen(1)
        c, a = self.sock.accept()
        print "remote keyboard available"
        while True:
            data = c.recv(2)
            if data in RKEYMAP:
                pos, key = RKEYMAP[data]
                self.cpu.keys[pos] = key

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
        if not opcode in self.funcmap0: opcode = self.opcode & 0xF000
        if opcode in self.funcmap0:
            self.funcmap0[opcode]()
        else:
            print "Unknown opcode: 0x%X" % self.opcode
    
    def _0NNN(self):
        # Ignored
        pass
    
    def _00E0(self):
        self.display.set_screen_size(*self.display.get_screen_size())
        self.display.update()
    
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
        self.V[self.x] &= 0xFF
    
    def _7XNN(self):
        self.V[self.x] += self.nn
        self.V[self.x] &= 0xFF
    
    def _8XYZ(self):
        opcode = self.opcode & 0xF00F
        if opcode in self.funcmap8:
            self.funcmap8[opcode]()
        else:
            print "Unknown opcode: 0x%X" % self.opcode
    
    def _8XY0(self):
        self.V[self.x] = self.V[self.y]
        self.V[self.x] &= 0xFF
    
    def _8XY1(self):
        self.V[self.x] |= self.V[self.y]
        self.V[self.x] &= 0xFF
    
    def _8XY2(self):
        self.V[self.x] &= self.V[self.y]
        self.V[self.x] &= 0xFF
    
    def _8XY3(self):
        self.V[self.x] ^= self.V[self.y]
        self.V[self.x] &= 0xFF
    
    def _8XY4(self):
        if self.V[self.x] + self.V[self.y] > 0xFF:
            self.V[0xF] = 1
        else:
            self.V[0xF] = 0
        self.V[self.x] += self.V[self.y]
        self.V[self.x] &= 0xFF
    
    def _8XY5(self):
        if self.V[self.x] > self.V[self.y]:
            self.V[0xF] = 1
        else:
            self.V[0xF] = 0
        self.V[self.x] -= self.V[self.y]
        self.V[self.x] &= 0xFF
    
    def _8XY6(self):
        self.V[0xF] = self.V[self.x] & 1
        self.V[self.x] >>= 1
    
    def _8XY7(self):
        self.V[self.x] = self.V[self.y] - self.V[self.x]
        self.V[0xF] = self.V[self.x] <= 0
        self.V[self.x] &= 0xFF
    
    def _8XYE(self):
        self.V[0xF] = (self.V[self.x] & 0x00F0) >> 7
        self.V[self.x] <<= 1
        self.V[self.x] &= 0xFF
    
    def _9XY0(self):
        if self.V[self.x] != self.V[self.y]:
            self.pc += 2
    
    def _ANNN(self):
        self.index = self.addr
    
    def _BNNN(self):
        self.pc = self.addr + self.V[0x0]
    
    def _CXNN(self):
        r = int(random.random() * 0xFF)
        self.V[self.x] = r & self.nn
        self.V[self.x] &= 0xFF
    
    def _DXYN(self):
        self.V[0xF] = 0
        x = self.V[self.x] & 0xFF
        y = self.V[self.y] & 0xFF
        height = self.opcode & 0x000F
        sx, sy = self.display.get_screen_size()
        for iy in xrange(height):
            py = (iy + y) % sy
            cbyte = bin(self.memory[self.index + iy])[2:].zfill(8)
            for ix in xrange(len(cbyte)):
                px = (ix + x) % sx
                
                color = int(cbyte[ix])
                ccolor = self.display.get_pixel(px, py)
                if color == ccolor == 1:
                    self.V[0xF] = 1
                
                self.display.set_pixel(px, py, color^ccolor)
        self.display.update()
    
    def _EXZZ(self):
        opcode = self.opcode & 0xF0FF
        if opcode in self.funcmapE:
            self.funcmapE[opcode]()
        else:
            print "Unknown opcode: 0x%X" % self.opcode
    
    def _EX9E(self):
        if self.keys[self.V[self.x] & 0xF] == 1:
            self.pc += 2
    
    def _EXA1(self):
        if self.keys[self.V[self.x] & 0xF] == 0:
            self.pc += 2
    
    def _FXZZ(self):
        opcode = self.opcode & 0xF0FF
        if opcode in self.funcmapF:
            self.funcmapF[opcode]()
        else:
            print "Unknown opcode: 0x%X" % self.opcode
    
    def _FX07(self):
        self.V[self.x] = self.delay_timer
    
    def _FX0A(self):
        key = self.get_key()
        if key == -1:
            self.pc -= 2
        else:
            self.V[self.x] = key
    
    def _FX15(self):
        self.delay_timer = self.V[self.x]
    
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
    
    def _FX55(self):
        for i in xrange(self.x):
            self.memory[self.index + i] = self.V[self.x]
        self.index += self.x + 1
    
    def _FX65(self):
        for i in xrange(self.x + 1):
            self.V[i] = self.memory[self.index + i]
        self.index += self.x + 1
    
    def initialize(self):
        """ See main docstring for info
        """
        self.opcode = 0
        self.memory = [0] * 4096
        
        self.V = [0] * 16
        self.index = 0
        self.pc    = 0x200 # 512
        
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
            0x9000: self._9XY0,
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
            0x8006: self._8XY6,
            0x8007: self._8XY7,
            0x800E: self._8XYE
        }
        
        self.funcmapE = {
            0xE09E: self._EX9E,
            0xE0A1: self._EXA1,
        }
        
        self.funcmapF = {
            0xF007: self._FX07,
            0xF00A: self._FX0A,
            0xF015: self._FX15,
            0xF018: self._FX18,
            0xF01E: self._FX1E,
            0xF029: self._FX29,
            0xF033: self._FX33,
            0xF055: self._FX55,
            0xF065: self._FX65,
        }
        self.kbd = remotekbd(self)
    
    def beep(self):
        print "BEEP!"
    
    def load(self, fp):
        data = fp.read()
        for i in xrange(len(data)):
            self.memory[i + 0x200] = ord(data[i])
    
    def cycle(self):
        self.opcode = self.memory[self.pc] << 8 | self.memory[self.pc + 1]
        # Support for VIP games; 64x64 screen
        if self.pc == 0x200 and self.opcode == 0x1260:
            global SCR_SIZE
            SCR_SIZE = [64, 64]
            self.gfx = [0] * SCR_SIZE[0] * SCR_SIZE[1]
            self.opcode = 0x12C0
            self.display.prev = self.gfx[:]
            self.display.display = pygame.display.set_mode(
                                              (SIZE[0] * SCR_SIZE[0],
                                               SIZE[1] * SCR_SIZE[1]))
        inst = self.opcode & 0xF000
        
        self.pc += 2
        self.x = ((self.opcode & 0x0F00) >> 8)
        self.y = ((self.opcode & 0x00F0) >> 4)
        self.addr = self.opcode & 0x0FFF
        self.nn = self.opcode & 0x00FF
        if inst in self.funcmap:
            self.funcmap[inst]()
        else:
            print ("Unknown opcodse: 0x%X" % self.opcode)
        
        if self.delay_timer > 0:
            self.delay_timer -= 1
        
        if self.sound_timer > 0:
            self.sound_timer -= 1
            if self.sound_timer == 0:
                self.beep()
    
    def process_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                pygame.quit()
                return False
            elif event.type == pygame.KEYDOWN:
                key = event.key
                if key in KEYMAP:
                    self.keys[KEYMAP[key]] = 1
            elif event.type == pygame.KEYUP:
                key = event.key
                if key in KEYMAP:
                    self.keys[KEYMAP[key]] = 0
        return self.running
    
    def get_key(self):
        for i in xrange(16):
            if self.keys[i]: return i
        return -1
    
    def mainloop(self, ROM, FPS, sfile):
        self.initialize()
        self.load(ROM)
        self.display = display()
        clock = pygame.time.Clock()
        
        # self.process_events() may set self.running to False,
        # that's why it is in the while loop
        # 
        # I am using `or` because self.process_events always returns None,
        # and we don't really care about it. It is just there to be
        # executed before the loop body starts
        while self.process_events():
            self.cycle()
            clock.tick(FPS)
    
    def _main(self):
        try:
            self.main()
        except KeyboardInterrupt:
            print "Interrupted\n"
            return
        except SystemExit:
            return
        except:
            print "An exception has occured during the emulation process:"
            print "~" * 80
            traceback.print_exc()
            print "~" * 80
    
    def main(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("rom", type=argparse.FileType("rb"),
                            help="CHIP-8 ROM to run")
        parser.add_argument("-f", "--fps", default=60, type=int,
                            help="frames per second")
        parser.add_argument("-s", "--sound-file", default="buzz.wav",
                            help="beep sound")
        
        args = parser.parse_args()
        self.mainloop(args.rom, args.fps, args.sound_file)

if __name__ == "__main__":
    chip8()._main()
