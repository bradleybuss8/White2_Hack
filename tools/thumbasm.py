"""Assemble a Thumb snippet at a fixed address with GNU binutils.

assemble(src, addr, syms) -> bytes. `syms` maps names to absolute addresses
(Thumb functions with bit 0 set, so BL resolves correctly).
"""
import os
import subprocess
import tempfile

PREFIX = 'arm-none-eabi-'
HEADER = '.syntax unified\n.cpu arm946e-s\n.thumb\n.section .text\n'


def assemble(src, addr, syms=None):
    syms = syms or {}
    pad = addr & 3
    if pad:
        return assemble('.space %d\n' % pad + src, addr - pad, syms)[pad:]
    with tempfile.TemporaryDirectory() as td:
        s, o, e, b = (os.path.join(td, n) for n in ('a.s', 'a.o', 'a.elf', 'a.bin'))
        defs = ''.join('.thumb_set %s, 0x%X\n' % (k, v) for k, v in syms.items() if v & 1)
        defs += ''.join('.set %s, 0x%X\n' % (k, v) for k, v in syms.items() if not v & 1)
        with open(s, 'w') as f:
            f.write(HEADER + defs + src + '\n')
        subprocess.run([PREFIX + 'as', '-mthumb-interwork', '-o', o, s], check=True)
        args = [PREFIX + 'ld', '-Ttext=0x%X' % addr, '-o', e, o]
        subprocess.run(args, check=True, capture_output=True)
        subprocess.run([PREFIX + 'objcopy', '-O', 'binary', '-j', '.text', e, b], check=True)
        return open(b, 'rb').read()
