#!/usr/bin/env python3
"""Re-compress a patched BLZ (bottom-LZ) blob while reusing the original token stream.

ARM9 and overlays on the DS are BLZ-compressed. Recompressing a lightly patched
binary from scratch changes the token count, which shifts every 8-token flag
group after the edit and rewrites most of the compressed file. Instead, this
keeps the original tokens and only re-encodes a small window around each token
that no longer decodes to the new data, using exactly as many tokens as the
window had. The flag groups stay aligned, so the compressed output differs from
the original only near the edits.

Usage as a module: blzpatch.recompress(orig_compressed, new_decompressed) -> bytes
"""
import struct

MIN_MATCH, MAX_MATCH = 3, 18
MIN_DIST, MAX_DIST = 3, 0x1002


def parse(blob):
    """Split a BLZ blob into (raw_prefix, tokens, last_flag_byte, decompressed_len).

    Tokens are in decode order, in the inverted domain (position 0 = last byte of the
    data): ('L', byte) or ('M', length, distance)."""
    v1, extra = struct.unpack_from('<II', blob, len(blob) - 8)
    comp_len, hdr_len = v1 & 0xFFFFFF, v1 >> 24
    raw_len = len(blob) - comp_len
    dec_len = len(blob) + extra
    stream = blob[raw_len:len(blob) - hdr_len][::-1]
    need = dec_len - raw_len
    tokens, i, out, flag = [], 0, 0, 0
    while out < need:
        flag = stream[i]
        i += 1
        for bit in range(8):
            if out >= need:
                break
            if flag & (0x80 >> bit):
                b0, b1 = stream[i], stream[i + 1]
                i += 2
                length, dist = (b0 >> 4) + MIN_MATCH, (((b0 & 0xF) << 8) | b1) + MIN_DIST
                tokens.append(('M', length, dist))
                out += length
            else:
                tokens.append(('L', stream[i]))
                i += 1
                out += 1
    if i != len(stream):
        raise ValueError('trailing data in BLZ stream')
    return blob[:raw_len], tokens, flag, dec_len


def token_len(t):
    return 1 if t[0] == 'L' else t[1]


def valid(t, inv, x):
    if t[0] == 'L':
        return inv[x] == t[1]
    length, dist = t[1], t[2]
    if x < dist:
        return False
    return all(inv[x + k] == inv[x + k - dist] for k in range(length))


def reencode(inv, s, e, counts):
    """Encode inv[s:e] with a token count from `counts` (tried in order), or return None."""
    best = {}
    for y in range(s, e):
        hi = min(MAX_DIST, y)
        bl, bd = 0, 0
        for d in range(MIN_DIST, hi + 1):
            n = 0
            while n < MAX_MATCH and y + n < e and inv[y + n] == inv[y + n - d]:
                n += 1
            if n > bl:
                bl, bd = n, d
                if n == MAX_MATCH:
                    break
        best[y] = (bl, bd)
    # reach[y] = {token count: (prev_y, token)}
    reach = {s: {0: None}}
    for y in range(s, e):
        if y not in reach:
            continue
        for c in list(reach[y]):
            if c >= max(counts):
                continue
            steps = [(y + 1, ('L', inv[y]))]
            bl, bd = best[y]
            for length in range(MIN_MATCH, bl + 1):
                steps.append((y + length, ('M', length, bd)))
            for ny, tok in steps:
                if ny <= e:
                    reach.setdefault(ny, {}).setdefault(c + 1, (y, c, tok))
    count = next((c for c in counts if c in reach.get(e, {})), None)
    if count is None:
        return None
    out, y, c = [], e, count
    while y != s:
        py, pc, tok = reach[y][c]
        out.append(tok)
        y, c = py, pc
    return out[::-1]


def recompress(orig_blob, new_data):
    raw, tokens, last_flag, dec_len = parse(orig_blob)
    if len(new_data) != dec_len:
        raise ValueError('decompressed size changed')
    if new_data[:len(raw)] != raw:
        raise ValueError('patch touches the uncompressed prefix; update it separately')
    inv = bytes(new_data[len(raw):])[::-1]
    starts, x = [], 0
    for t in tokens:
        starts.append(x)
        x += token_len(t)
    starts.append(x)

    tokens = list(tokens)
    j = 0
    while j < len(tokens):
        t = tokens[j]
        if t[0] == 'L':
            tokens[j] = ('L', inv[starts[j]])
            j += 1
            continue
        if valid(t, inv, starts[j]):
            j += 1
            continue
        for radius in list(range(1, 64)) + list(range(64, 512, 16)):
            a, b = max(0, j - radius), min(len(tokens), j + radius + 1)
            # same count keeps every later flag group intact; +-8k shifts them by whole groups
            n = b - a
            counts = [n] + [n + 8 * k * sign for k in range(1, 33) for sign in (1, -1)]
            enc = reencode(inv, starts[a], starts[b], [c for c in counts if c > 0])
            if enc is not None:
                x = starts[a]
                tokens[a:b] = enc
                new_starts = []
                for tok in enc:
                    new_starts.append(x)
                    x += token_len(tok)
                starts[a:b] = new_starts
                b = a + len(enc)
                break
        else:
            raise ValueError(f'could not re-encode around token {j}')
        j = b

    # rebuild the stream (inverted domain), keeping the original's unused trailing flag bits
    stream = bytearray()
    for g in range(0, len(tokens), 8):
        group = tokens[g:g + 8]
        flag = 0
        for k, tok in enumerate(group):
            if tok[0] == 'M':
                flag |= 0x80 >> k
        if len(group) < 8:
            flag |= last_flag & (0xFF >> len(group))
        stream.append(flag)
        for tok in group:
            if tok[0] == 'L':
                stream.append(tok[1])
            else:
                length, dist = tok[1], tok[2]
                stream.append(((length - MIN_MATCH) << 4) | ((dist - MIN_DIST) >> 8))
                stream.append((dist - MIN_DIST) & 0xFF)
    pad = (-(len(raw) + len(stream))) % 4
    hdr_len = 8 + pad
    out = bytearray(raw) + stream[::-1] + b'\xFF' * pad
    out += struct.pack('<II', (len(stream) + hdr_len) | (hdr_len << 24), dec_len - len(out) - 8)
    return bytes(out)
