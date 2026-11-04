"""Patch members of a NARC without repacking it (keeps the xdelta small).

Changed or new members are appended to the end of the FIMG block and only their
FATB entries are rewritten; untouched members keep their bytes and offsets.
"""
import struct


def patch_narc(data, changes):
    """changes: {index: bytes}; an index equal to the member count appends a new member."""
    data = bytes(data)
    assert data[:4] == b'NARC'
    hdr_size = struct.unpack_from('<H', data, 0xC)[0]
    fatb = hdr_size
    assert data[fatb:fatb + 4] == b'BTAF'
    fatb_size, count = struct.unpack_from('<IH', data, fatb + 4)
    entries = [list(struct.unpack_from('<II', data, fatb + 12 + 8 * i)) for i in range(count)]
    fntb = fatb + fatb_size
    assert data[fntb:fntb + 4] == b'BTNF'
    fntb_blk = data[fntb:fntb + struct.unpack_from('<I', data, fntb + 4)[0]]
    fimg = fntb + len(fntb_blk)
    assert data[fimg:fimg + 4] == b'GMIF'
    img = bytearray(data[fimg + 8:fimg + struct.unpack_from('<I', data, fimg + 4)[0]])

    for idx in sorted(changes):
        blob = changes[idx]
        if len(img) % 4:
            img += b'\xff' * (4 - len(img) % 4)
        start = len(img)
        img += blob
        if idx == len(entries):
            entries.append([start, start + len(blob)])
        elif idx < len(entries):
            entries[idx] = [start, start + len(blob)]
        else:
            raise IndexError(idx)
    if len(img) % 4:
        img += b'\xff' * (4 - len(img) % 4)

    fat = b'BTAF' + struct.pack('<IHH', 12 + 8 * len(entries), len(entries), 0)
    fat += b''.join(struct.pack('<II', s, e) for s, e in entries)
    out = data[:hdr_size] + fat + fntb_blk + b'GMIF' + struct.pack('<I', 8 + len(img)) + bytes(img)
    out = bytearray(out)
    struct.pack_into('<I', out, 8, len(out))
    return bytes(out)
