#!/usr/bin/env python3
"""Tiny headless DeSmuME driver (py-desmume) used to smoke-test the patched ROM.

Run with SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy.
"""
import os

from desmume.controls import Keys, keymask
from desmume.emulator import DeSmuME

KEYS = {
    'A': Keys.KEY_A, 'B': Keys.KEY_B, 'X': Keys.KEY_X, 'Y': Keys.KEY_Y,
    'L': Keys.KEY_L, 'R': Keys.KEY_R, 'START': Keys.KEY_START, 'SELECT': Keys.KEY_SELECT,
    'UP': Keys.KEY_UP, 'DOWN': Keys.KEY_DOWN, 'LEFT': Keys.KEY_LEFT, 'RIGHT': Keys.KEY_RIGHT,
}


class Emu:
    def __init__(self, rom, outdir):
        self.emu = DeSmuME()
        self.emu.open(rom)
        self.emu.volume_set(0)
        self.outdir = outdir
        self.frame = 0
        os.makedirs(outdir, exist_ok=True)

    def run(self, n):
        for _ in range(n):
            self.emu.cycle(with_joystick=False)
            self.frame += 1

    def press(self, key, hold=4, after=20):
        k = keymask(KEYS[key])
        self.emu.input.keypad_add_key(k)
        self.run(hold)
        self.emu.input.keypad_rm_key(k)
        self.run(after)

    def touch(self, x, y, hold=6, after=20):
        self.emu.input.touch_set_pos(x, y)
        self.run(hold)
        self.emu.input.touch_release()
        self.run(after)

    def shot(self, name):
        path = os.path.join(self.outdir, name + '.png')
        self.emu.screenshot().save(path)
        return path

    def save_state(self, path):
        self.emu.savestate.save_file(path)

    def load_state(self, path):
        self.emu.savestate.load_file(path)

    def read8(self, addr):
        return self.emu.memory.unsigned[addr]


def hold(e, key, frames, after=8):
    k = keymask(KEYS[key])
    e.emu.input.keypad_add_key(k)
    e.run(frames)
    e.emu.input.keypad_rm_key(k)
    e.run(after)


def read16(e, addr):
    m = e.emu.memory.unsigned
    return m[addr] | (m[addr + 1] << 8)


def walk_to(e, tx, tz, pos_addr, max_steps=60, zoff=4):
    """Greedy tile walk; pos_addr points at x, z is zoff bytes later."""
    for _ in range(max_steps):
        x, z = read16(e, pos_addr), read16(e, pos_addr + zoff)
        if (x, z) == (tx, tz):
            return True
        if x != tx:
            hold(e, 'RIGHT' if tx > x else 'LEFT', 16)
        else:
            hold(e, 'DOWN' if tz > z else 'UP', 16)
    return False
