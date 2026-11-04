"""Gen 5 (Black 2 / White 2) message banks: decode and encode.

A bank is one section of UTF-16 strings; string i is XOR-encrypted with a key that
starts at 0x7C89 + 0x2983 * i and is rotated left by 3 bits after every character.

Text escapes understood by encode()/decode():
  \\n -> 0xFFFE (new line), {WAIT} -> scroll after a button press,
  {CLEAR} -> clear the box after a button press, {PLAYER} -> word buffer 0 (player),
  {MON0} -> word buffer 0 (party Pokemon nickname), {MOVE0} -> word buffer 0 (move name),
  {Fxxxx ...} -> raw control codes (hex u16s after the leading F000).
"""
import re
import struct

KEY0, KEY_STEP = 0x7C89, 0x2983

CTRL = {
    'WAIT': (0xBE01, 0x0000),
    'CLEAR': (0xBE00, 0x0000),
    'PLAYER': (0x0100, 0x0001, 0x0000),
    'MON0': (0x0102, 0x0001, 0x0000),
    'MOVE0': (0x0106, 0x0001, 0x0000),
}


def _rotl(k):
    return ((k << 3) | (k >> 13)) & 0xFFFF


def _crypt(chars, index):
    key = (KEY0 + KEY_STEP * index) & 0xFFFF
    out = []
    for c in chars:
        out.append(c ^ key)
        key = _rotl(key)
    return out


def decode_bank(data):
    """-> list of (chars without terminator, unk) ; chars are u16 lists."""
    nsec, nent, secsize, _ = struct.unpack_from('<HHII', data, 0)
    if nsec != 1:
        raise ValueError('expected one section')
    so = struct.unpack_from('<I', data, 12)[0]
    out = []
    for i in range(nent):
        o, n, unk = struct.unpack_from('<IHH', data, so + 4 + 8 * i)
        chars = _crypt(struct.unpack_from('<%dH' % n, data, so + o), i)
        if chars and chars[-1] == 0xFFFF:
            chars = chars[:-1]
        out.append((chars, unk))
    return out


def encode_bank(entries):
    """entries: list of (chars, unk) as returned by decode_bank."""
    n = len(entries)
    body = b''
    table = b''
    base = 4 + 8 * n
    for i, (chars, unk) in enumerate(entries):
        chars = list(chars) + [0xFFFF]
        table += struct.pack('<IHH', base + len(body), len(chars), unk)
        body += struct.pack('<%dH' % len(chars), *_crypt(chars, i))
    sec = table + body
    if len(sec) % 4:
        sec += b'\0' * (4 - len(sec) % 4)
    secsize = 4 + len(sec)
    return struct.pack('<HHIII', 1, n, secsize, 0, 16) + struct.pack('<I', secsize) + sec


def to_text(chars):
    s, i = '', 0
    while i < len(chars):
        c = chars[i]
        if c == 0xFFFE:
            s += '\\n'
        elif c == 0xF000:
            kind, argc = chars[i + 1], chars[i + 2] if i + 2 < len(chars) else 0
            for name, seq in CTRL.items():
                if tuple(chars[i + 1:i + 1 + len(seq)]) == seq:
                    s += '{%s}' % name
                    i += len(seq)
                    break
            else:
                n = 2 + (argc if kind & 0xFF00 != 0xBE00 else 0)
                s += '{F' + ' '.join('%04X' % x for x in chars[i + 1:i + 1 + n]) + '}'
                i += n
        else:
            s += chr(c)
        i += 1
    return s


def from_text(s):
    out = []
    for tok in re.split(r'(\{[^}]*\}|\\n)', s):
        if not tok:
            continue
        if tok == '\\n':
            out.append(0xFFFE)
        elif tok.startswith('{F') and tok[2:3] != '}' and tok[1:-1] not in CTRL:
            out += [0xF000] + [int(x, 16) for x in tok[2:-1].split()]
        elif tok.startswith('{'):
            out += [0xF000] + list(CTRL[tok[1:-1]])
        else:
            out += [ord(ch) for ch in tok]
    return out
