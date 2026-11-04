"""QoL data changes: trade evolutions happen by level instead.

Evolution data (a/0/1/9): one 42-byte file per species, 7 x (u16 method, u16 param,
u16 target). Methods used here: 4 level, 5 trade, 6 trade holding an item, 7 trade for
a specific Pokemon, 23 level (male), 24 level (female). Every replaced entry is checked
against the vanilla value first.
"""
import struct
import sys

import narcpatch

EVO_NARC = 'a/0/1/9'
LEVEL, TRADE, TRADE_ITEM, TRADE_SPECIES, LEVEL_MALE, LEVEL_FEMALE = 4, 5, 6, 7, 23, 24

# species: [(slot, vanilla (method, param, target), new (method, param, target))]
TRADE_EVOS = {
    64: [(0, (TRADE, 0, 65), (LEVEL, 37, 65))],              # Kadabra -> Alakazam
    67: [(0, (TRADE, 0, 68), (LEVEL, 37, 68))],              # Machoke -> Machamp
    75: [(0, (TRADE, 0, 76), (LEVEL, 37, 76))],              # Graveler -> Golem
    93: [(0, (TRADE, 0, 94), (LEVEL, 37, 94))],              # Haunter -> Gengar
    61: [(1, (TRADE_ITEM, 221, 186), (LEVEL, 37, 186))],     # Poliwhirl -> Politoed (Water Stone: Poliwrath)
    79: [(0, (LEVEL, 37, 80), (LEVEL_MALE, 37, 80)),         # Slowpoke: male -> Slowbro,
         (1, (TRADE_ITEM, 221, 199), (LEVEL_FEMALE, 37, 199))],  # female -> Slowking
    95: [(0, (TRADE_ITEM, 233, 208), (LEVEL, 35, 208))],     # Onix -> Steelix
    123: [(0, (TRADE_ITEM, 233, 212), (LEVEL, 35, 212))],    # Scyther -> Scizor
    137: [(0, (TRADE_ITEM, 252, 233), (LEVEL, 30, 233))],    # Porygon -> Porygon2
    117: [(0, (TRADE_ITEM, 235, 230), (LEVEL, 45, 230))],    # Seadra -> Kingdra
    233: [(0, (TRADE_ITEM, 324, 474), (LEVEL, 45, 474))],    # Porygon2 -> Porygon-Z
    125: [(0, (TRADE_ITEM, 322, 466), (LEVEL, 50, 466))],    # Electabuzz -> Electivire
    126: [(0, (TRADE_ITEM, 323, 467), (LEVEL, 50, 467))],    # Magmar -> Magmortar
    356: [(0, (TRADE_ITEM, 325, 477), (LEVEL, 50, 477))],    # Dusclops -> Dusknoir
    112: [(0, (TRADE_ITEM, 321, 464), (LEVEL, 55, 464))],    # Rhydon -> Rhyperior
    366: [(0, (TRADE_ITEM, 226, 367), (LEVEL_MALE, 30, 367)),    # Clamperl: male -> Huntail,
          (1, (TRADE_ITEM, 227, 368), (LEVEL_FEMALE, 30, 368))],  # female -> Gorebyss
    349: [(1, (TRADE_ITEM, 537, 350), (LEVEL, 35, 350))],    # Feebas -> Milotic
    525: [(0, (TRADE, 0, 526), (LEVEL, 37, 526))],           # Boldore -> Gigalith
    533: [(0, (TRADE, 0, 534), (LEVEL, 37, 534))],           # Gurdurr -> Conkeldurr
    588: [(0, (TRADE_SPECIES, 0, 589), (LEVEL, 30, 589))],   # Karrablast -> Escavalier
    616: [(0, (TRADE_SPECIES, 0, 617), (LEVEL, 30, 617))],   # Shelmet -> Accelgor
}


def patch_evolutions(narc_raw, narc):
    changes = {}
    for sp, edits in TRADE_EVOS.items():
        f = bytearray(narc.files[sp])
        for slot, old, new in edits:
            cur = struct.unpack_from('<3H', f, 6 * slot)
            if cur != old:
                sys.exit(f'evolution data for species {sp} slot {slot} is {cur}, expected {old}')
            struct.pack_into('<3H', f, 6 * slot, *new)
        changes[sp] = bytes(f)
    return narcpatch.patch_narc(narc_raw, changes)


def apply(rom, out):
    import ndspy.narc
    raw = rom.getFileByName(EVO_NARC)
    out.set_file(rom.filenames.idOf(EVO_NARC), patch_evolutions(raw, ndspy.narc.NARC(raw)))
