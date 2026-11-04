#!/usr/bin/env python3
"""Build Pokemon White 2 (USA) with a Porta-PC button in the X menu and QoL changes.

Port of the HeartGold Porta-PC (../../pokemon_platinum_patch_master hg_portapc):
a PC button on the bottom bar of the X menu opens the Porta-PC menu
(MOVE POKEMON / MOVE ITEMS / BATTLE BOX / HEAL PARTY / REPEL: ON-OFF / RELEARN MOVES /
GIVE STATUS / SEE YA!). See README.md.

Usage:
  python3 -I build.py --rom "Pokemon - White Version 2 (USA, Europe) (NDSi Enhanced).nds" --out out.nds
"""
import argparse
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))

import ndspy.code  # noqa: E402
import ndspy.codeCompression  # noqa: E402
import ndspy.narc  # noqa: E402
import ndspy.rom  # noqa: E402

import blzpatch  # noqa: E402
import freespace  # noqa: E402
import gfx  # noqa: E402
import gen5msg  # noqa: E402
import gen5script  # noqa: E402
import narcpatch  # noqa: E402
import romwriter  # noqa: E402

import menu_patches  # noqa: E402
import ov12_patches  # noqa: E402
import portapc_script  # noqa: E402
import qol  # noqa: E402
import repel_patch  # noqa: E402
import syms  # noqa: E402

VANILLA_SHA1 = 'b5d7490be7b415b8f1e672a53e978a9cc667e56a'   # Pokemon White 2 (USA, IRDO)

SYS_MSG_NARC = 'a/0/0/2'
STORY_MSG_NARC = 'a/0/0/3'
SCRIPT_NARC = 'a/0/5/6'
FIELD_MENU_BANK = 38          # X-menu labels (20 entries)

REPEL_FLAG = 550              # unused event flag (no script, NPC or trainer uses 498-603)


def apply_edits(data, base, edits, what):
    for addr, old, new in edits:
        off = addr - base
        if not 0 <= off <= len(data) - len(new):
            sys.exit(f'{what}: edit at 0x{addr:08X} is outside the overlay')
        if old is not None and bytes(data[off:off + len(old)]) != old:
            sys.exit(f'{what}: unexpected bytes at 0x{addr:08X} '
                     f'({bytes(data[off:off + len(old)]).hex()} != {old.hex()})')
        data[off:off + len(new)] = new


def save_overlay_patched(ov, orig_file):
    packed = blzpatch.recompress(orig_file, bytes(ov.data))
    if ndspy.codeCompression.decompress(packed) != bytes(ov.data):
        sys.exit(f'overlay file {ov.fileID}: BLZ round trip failed')
    ov.compressedSize = len(packed)
    return packed


def append_strings(narc, bank, texts, expect_count):
    entries = gen5msg.decode_bank(narc.files[bank])
    if len(entries) != expect_count:
        sys.exit(f'message bank {bank}: expected {expect_count} entries, found {len(entries)}')
    first = len(entries)
    for t in texts:
        entries.append((gen5msg.from_text(t), 0))
    return first, gen5msg.encode_bank(entries)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--rom', required=True, help='vanilla Pokemon White 2 (USA) .nds')
    ap.add_argument('--out', required=True)
    ap.add_argument('--skip', default='', help='debug: comma list of parts to leave vanilla (text,script,ov12,ov36,qol)')
    args = ap.parse_args()
    skip = set(filter(None, args.skip.split(',')))

    data = open(args.rom, 'rb').read()
    if hashlib.sha1(data).hexdigest() != VANILLA_SHA1:
        sys.exit('input ROM is not a clean Pokemon White 2 (USA) dump (SHA-1 mismatch)')
    rom = ndspy.rom.NintendoDSRom(data)
    out = romwriter.RomImage(data)

    # ---- text
    sys_raw = rom.getFileByName(SYS_MSG_NARC)
    sys_msg = ndspy.narc.NARC(sys_raw)
    pc_label, bank38 = append_strings(sys_msg, FIELD_MENU_BANK, ['PC'], 20)
    if pc_label != menu_patches.MSG_PC_LABEL:
        sys.exit('unexpected PC label index')
    sys_changes = {FIELD_MENU_BANK: bank38}

    story_raw = rom.getFileByName(STORY_MSG_NARC)
    story = ndspy.narc.NARC(story_raw)
    first_msg, bank = append_strings(story, portapc_script.TEXT_BANK,
                                     [t for _, t in portapc_script.TEXTS], 42)
    story_changes = {portapc_script.TEXT_BANK: bank}

    # ---- Porta-PC script
    scr_raw = rom.getFileByName(SCRIPT_NARC)
    scr = ndspy.narc.NARC(scr_raw)
    script, _ = portapc_script.build(first_msg, REPEL_FLAG)
    new_file, idx = gen5script.append_script(scr.files[portapc_script.SCRIPT_FILE], script)
    script_id = portapc_script.SCRIPT_FIRST_ID + idx
    if idx != 1:
        sys.exit(f'Porta-PC script landed at index {idx}, expected 1')
    if 'script' not in skip:
        out.set_file(rom.filenames.idOf(SCRIPT_NARC),
                     narcpatch.patch_narc(scr_raw, {portapc_script.SCRIPT_FILE: new_file}))

    # ---- X-menu graphics: PC icon and the PC button frame on the bottom bar
    gfx_raw = rom.getFileByName(gfx.MENU_GFX_NARC)
    gfx_narc = ndspy.narc.NARC(gfx_raw)
    gfx_changes = {gfx.PC_ICON_NCGR: gfx.pc_icon(gfx_narc.files[gfx.PC_ICON_NCGR])}
    for i in gfx.BUTTON_NSCR:
        gfx_changes[i] = gfx.add_bar_button(gfx_narc.files[i])
    out.set_file(rom.filenames.idOf(gfx.MENU_GFX_NARC), narcpatch.patch_narc(gfx_raw, gfx_changes))

    # ---- overlays
    ovt = rom.loadArm9Overlays()
    ov12 = bytearray(ovt[12].data)
    ov36 = bytearray(ovt[36].data)
    for d, base, (lo, hi), name in ((ov12, syms.OV12_BASE, syms.OV12_FREE, 'overlay 12'),
                                    (ov36, syms.OV36_BASE, syms.OV36_FREE, 'overlay 36')):
        try:
            freespace.check(bytes(d), base, lo, hi)
        except ValueError as e:
            sys.exit(f'{name}: free space is in use: {e}')

    menu = menu_patches.edits()
    used36 = menu_patches.USED_FREE_END
    repel, n = repel_patch.build((used36 + 3) & ~3, REPEL_FLAG)
    used36 = ((used36 + 3) & ~3) + n
    if used36 > syms.OV36_FREE[1]:
        sys.exit('overlay 36 free space overflow')
    apply_edits(ov36, syms.OV36_BASE, menu + repel, 'overlay 36')

    e12, used12 = ov12_patches.build(script_id, menu_patches.ITEM_PC)
    apply_edits(ov12, syms.OV12_BASE, e12, 'overlay 12')

    # ---- QoL data
    if 'qol' not in skip:
        qol.apply(rom, out, story, story_changes)

    if 'text' not in skip:
        out.set_file(rom.filenames.idOf(SYS_MSG_NARC), narcpatch.patch_narc(sys_raw, sys_changes))
        out.set_file(rom.filenames.idOf(STORY_MSG_NARC), narcpatch.patch_narc(story_raw, story_changes))

    for i, d in ((12, ov12), (36, ov36)):
        if f'ov{i}' in skip:
            continue
        ovt[i].data = bytes(d)
        out.set_file(ovt[i].fileID, save_overlay_patched(ovt[i], rom.files[ovt[i].fileID]))
    out.set_arm9_overlay_table(ndspy.code.saveOverlayTable(ovt))

    open(args.out, 'wb').write(out.finish())
    print(f'wrote {args.out}')
    print(f'  Porta-PC script ID {script_id}, bank {portapc_script.TEXT_BANK} strings #{first_msg}+, '
          f'repel flag {REPEL_FLAG}')
    print(f'  free space: overlay 12 {used12}/{syms.OV12_FREE[1] - syms.OV12_FREE[0]} bytes, '
          f'overlay 36 {used36 - syms.OV36_FREE[0]}/{syms.OV36_FREE[1] - syms.OV36_FREE[0]} bytes')


if __name__ == '__main__':
    main()
