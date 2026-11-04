"""Build / decrypt a Gen 5 party Pokemon (220 bytes) for test setup in emulator RAM.

Layout as documented for PK5 (PKHeX): 8-byte header, four shuffled 32-byte blocks
encrypted with an LCG seeded by the checksum, and an 84-byte party tail encrypted
with the same LCG seeded by the PID.
"""
import struct

ORDERS = ['ABCD', 'ABDC', 'ACBD', 'ACDB', 'ADBC', 'ADCB', 'BACD', 'BADC', 'BCAD', 'BCDA', 'BDAC', 'BDCA',
          'CABD', 'CADB', 'CBAD', 'CBDA', 'CDAB', 'CDBA', 'DABC', 'DACB', 'DBAC', 'DBCA', 'DCAB', 'DCBA']


def _crypt(data, seed):
    out = bytearray()
    for i in range(0, len(data), 2):
        seed = (seed * 0x41C64E6D + 0x6073) & 0xFFFFFFFF
        out += struct.pack('<H', struct.unpack_from('<H', data, i)[0] ^ (seed >> 16))
    return bytes(out)


def encode(plain):
    """plain: 220 bytes, unshuffled/decrypted (blocks A,B,C,D at 0x08..0x87)."""
    pid = struct.unpack_from('<I', plain, 0)[0]
    body = plain[8:136]
    chk = sum(struct.unpack('<64H', body)) & 0xFFFF
    order = ORDERS[((pid >> 13) & 31) % 24]
    blocks = [body[32 * i:32 * i + 32] for i in range(4)]
    shuffled = b''.join(blocks['ABCD'.index(c)] for c in order)
    return (struct.pack('<IHH', pid, 0, chk) + _crypt(shuffled, chk) + _crypt(plain[136:220], pid))


def decode(raw):
    pid, _, chk = struct.unpack_from('<IHH', raw, 0)
    body = _crypt(raw[8:136], chk)
    order = ORDERS[((pid >> 13) & 31) % 24]
    blocks = {c: body[32 * i:32 * i + 32] for i, c in enumerate(order)}
    plain = raw[:8] + b''.join(blocks[c] for c in 'ABCD') + _crypt(raw[136:220], pid)
    ok = sum(struct.unpack('<64H', plain[8:136])) & 0xFFFF == chk
    return plain, ok


def make(species, level, exp, moves, nickname, pid=0x12345678, nature=0, ability=1,
         stats=(20, 10, 10, 10, 10, 10), tid=12345, sid=54321, ot='TEST', version=23):
    p = bytearray(220)
    struct.pack_into('<I', p, 0x00, pid)
    struct.pack_into('<HHHHI', p, 0x08, species, 0, tid, sid, exp)
    p[0x14] = 70           # friendship
    p[0x15] = ability
    p[0x17] = 2            # English
    mv = list(moves) + [0] * (4 - len(moves))
    struct.pack_into('<4H', p, 0x28, *mv)
    for i, m in enumerate(mv):
        p[0x30 + i] = 35 if m else 0
    struct.pack_into('<I', p, 0x38, 0x3FFFFFFF)   # 31 IVs
    p[0x41] = nature
    name = [ord(c) for c in nickname] + [0xFFFF]
    name += [0xFFFF] * (11 - len(name))
    struct.pack_into('<11H', p, 0x48, *name[:11])
    p[0x5F] = version
    otn = [ord(c) for c in ot] + [0xFFFF]
    otn += [0xFFFF] * (8 - len(otn))
    struct.pack_into('<8H', p, 0x68, *otn[:8])
    struct.pack_into('<H', p, 0x80, 1)            # met location
    p[0x83] = 4            # Poke Ball
    p[0x84] = level
    struct.pack_into('<I', p, 0x88, 0)            # status
    p[0x8C] = level
    struct.pack_into('<7H', p, 0x8E, stats[0], stats[0], *stats[1:])
    return encode(bytes(p))
