#!/usr/bin/env python3
"""List Thumb BL/BLX call sites of a function in ARM9 and the overlays.

Usage: python3 -I callers.py <unpacked_rom_dir> <target_addr> [<target_addr> ...]
"""
import os
import struct
import sys


def blobs(rom):
    yield 'arm9', 0x02004000, open(os.path.join(rom, 'arm9.bin'), 'rb').read()
    for line in open(os.path.join(rom, 'overlays.txt')):
        f = line.split()
        ov, ram = int(f[0]), int(f[1].split('=')[1], 16)
        yield f'ov{ov:02d}', ram, open(os.path.join(rom, 'overlay', f'ov{ov:03d}.bin'), 'rb').read()


def calls(base, data):
    for i in range(0, len(data) - 3, 2):
        hi, lo = struct.unpack_from('<HH', data, i)
        if (hi & 0xF800) == 0xF000 and (lo & 0xE800) == 0xE800:
            off = ((hi & 0x7FF) << 12) | ((lo & 0x7FF) << 1)
            if off & 0x400000:
                off -= 0x800000
            t = base + i + 4 + off
            yield base + i, (t & ~3) if (lo & 0xF800) == 0xE800 else t


def main():
    rom = sys.argv[1]
    targets = {int(a, 0) & ~1 for a in sys.argv[2:]}
    for name, base, data in blobs(rom):
        for at, t in calls(base, data):
            if t in targets:
                print(f'{name} 0x{at:08X} -> 0x{t:08X}')


if __name__ == '__main__':
    main()
