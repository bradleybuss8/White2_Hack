"""Check that a byte range of an overlay holds only assert file-name strings.

Every 32-bit literal in the overlay that points into the range must be loaded by an
`ldr rX, [pc, #...]` that is followed (within 12 instructions) by a BL to
GFL_DebugAssertFail / GFL_DebugAssertFailEx (which only read the string when an assert
fires) or GFL_HeapAllocate (which copies at most 18 bytes of it into a debug field).
So the bytes can hold new code and data.
"""
import struct

ASSERT_FUNCS = (0x0203CBAC, 0x0203CBC0)
# Heap allocators take (heap, size, flags, file, line) and copy at most 18 bytes of
# `file` into the block's debug header, so new bytes there are harmless too.
HEAP_FUNCS = (0x0203A228,)
ALLOWED = ASSERT_FUNCS + HEAP_FUNCS


def _bl_target(data, i, base):
    hi, lo = struct.unpack_from('<HH', data, i)
    if (hi & 0xF800) != 0xF000 or (lo & 0xE800) != 0xE800:
        return None
    off = ((hi & 0x7FF) << 12) | ((lo & 0x7FF) << 1)
    if off & 0x400000:
        off -= 0x800000
    t = base + i + 4 + off
    return t & ~3 if (lo & 0xF800) == 0xE800 else t


def check(data, base, start, end):
    """Raise ValueError if anything but an assert call references [start, end)."""
    refs = []
    for lit in range(0, len(data) - 3, 4):
        v = struct.unpack_from('<I', data, lit)[0]
        if start <= v < end:
            refs.append(lit)
    for lit in refs:
        loads = [i for i in range(max(0, lit - 1020), lit, 2)
                 if (struct.unpack_from('<H', data, i)[0] & 0xF800) == 0x4800
                 and ((i + 4) & ~3) + (struct.unpack_from('<H', data, i)[0] & 0xFF) * 4 == lit]
        if not loads:
            raise ValueError('literal at 0x%08X points into free space but is not loaded by code'
                             % (base + lit))
        for ld in loads:
            if not any(_bl_target(data, j, base) in ALLOWED for j in range(ld + 2, ld + 26, 2)):
                raise ValueError('0x%08X loads a pointer into free space and is not an assert call'
                                 % (base + ld))
    return len(refs)
