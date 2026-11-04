"""Tiny assembler for Gen 5 field scripts (Black 2 / White 2).

A script file is a table of s32 offsets (relative to the end of each entry) ended by
0xFD13, followed by the bytecode. Each command is a u16 opcode plus fixed-size
arguments. Jumps and calls take an s32 offset relative to the end of the command.

Opcodes and argument sizes are from the Gen 5 script command reference shipped with
CTRMapV (SDK5-B2W2); only the commands used here are listed.
"""
import struct

# name: (opcode, argument sizes in bytes)
OPS = {
    'Halt': (0x02, ()),
    'Sleep': (0x03, (2,)),
    'Call': (0x04, (4,)),
    'Return': (0x05, ()),
    'SetPartyStatus': (0x07, (2, 2)),       # custom: replaces DebugStack (see ov12_patches)
    'CmpVarConst': (0x19, (2, 2)),
    'Jump': (0x1E, (4,)),
    'JumpIf': (0x1F, (1, 4)),
    'FlagSet': (0x23, (2,)),
    'FlagReset': (0x24, (2,)),
    'FlagGet': (0x25, (2, 2)),
    'SetVar': (0x28, (2, 2)),
    'ActorPauseAll': (0x2E, ()),
    'ActorUnlockAll': (0x2F, ()),
    'FinishSubEvents': (0x30, ()),
    'WaitButton': (0x32, ()),
    'Msg': (0x34, (2, 2)),
    'MsgClose': (0x36, ()),
    'WordSetPlayerName': (0x4C, (1,)),
    'WordSetPartyPokeName': (0x54, (1, 2)),
    'SEPlay': (0xA6, (2,)),
    'SEWait': (0xA8, ()),
    'MEPlay': (0xA9, (2,)),
    'MEWait': (0xAA, ()),
    'ListMenuAdd': (0xAF, (2, 2, 2)),
    'ListMenuShow': (0xB1, ()),
    'ListMenuInitTR': (0xB2, (1, 1, 2, 1, 2)),
    'PartyIsEgg': (0x102, (2, 2)),
    'PartyGetCount': (0x103, (2, 2)),
    'PartyRecoverAll': (0x104, ()),
    'CallPokeSelect': (0x107, (2, 2, 2, 2)),
    'CallPC': (0x14F, (2, 2)),
    'FadeInBlack': (0x1A3, ()),
    'FadeOutBlack': (0x1A4, ()),
    'FadeWait': (0x1A7, ()),
    'MoveReminderCheckPkm': (0x1D5, (2, 2)),
    'MoveReminderCallMoveSelect': (0x1D6, (2, 2)),
}
JUMPS = {'Call', 'Jump', 'JumpIf'}
EQ = 1           # condition code for JumpIf after CmpVarConst


class Script:
    def __init__(self):
        self.items = []      # ('raw', bytes) | ('label', name) | ('jump', opbytes, label)
        self.labels = {}

    def label(self, name):
        self.items.append(('label', name))

    def __getattr__(self, name):
        if name not in OPS:
            raise AttributeError(name)

        def emit(*args):
            op, sizes = OPS[name]
            if len(args) != len(sizes):
                raise TypeError('%s takes %d arguments' % (name, len(sizes)))
            head = struct.pack('<H', op)
            if name in JUMPS:
                for a, sz in zip(args[:-1], sizes[:-1]):
                    head += a.to_bytes(sz, 'little')
                self.items.append(('jump', head, args[-1]))
                return
            for a, sz in zip(args, sizes):
                head += (a & ((1 << (8 * sz)) - 1)).to_bytes(sz, 'little')
            self.items.append(('raw', head))
        return emit

    def assemble(self, base):
        """Bytecode for this script placed at file offset `base`."""
        pos, labels = base, {}
        for kind, *rest in self.items:
            if kind == 'label':
                labels[rest[0]] = pos
            elif kind == 'raw':
                pos += len(rest[0])
            else:
                pos += len(rest[0]) + 4
        out, pos = b'', base
        for kind, *rest in self.items:
            if kind == 'raw':
                out += rest[0]
                pos += len(rest[0])
            elif kind == 'jump':
                end = pos + len(rest[0]) + 4
                out += rest[0] + struct.pack('<i', labels[rest[1]] - end)
                pos = end
        return out


def script_offsets(data):
    offs, i = [], 0
    while struct.unpack_from('<H', data, i)[0] != 0xFD13:
        offs.append(i + 4 + struct.unpack_from('<i', data, i)[0])
        i += 4
    return offs, i


def append_script(data, script):
    """Append `script` to a script file. Returns (new_file, index)."""
    offs, i = script_offsets(data)
    n = len(offs)
    body = data[i + 2:]
    hdr_len = 4 * (n + 1) + 2
    shift = hdr_len - (i + 2)
    new_off = hdr_len + len(body)
    if new_off % 2:
        body += b'\0'
        new_off += 1
    hdr = b''.join(struct.pack('<i', (o + shift) - (4 * k + 4)) for k, o in enumerate(offs))
    hdr += struct.pack('<i', new_off - (4 * n + 4)) + struct.pack('<H', 0xFD13)
    return hdr + body + script.assemble(new_off), n
