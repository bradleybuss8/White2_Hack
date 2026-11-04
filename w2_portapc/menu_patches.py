"""Overlay 36 (field menu) edits: adds a PC button as menu slot 6, on the left of the
bottom bar, with the close "X" kept as a separate touch area.

Each entry is (address, expected_vanilla_bytes_or_None, new_bytes). Code is assembled
with tools/thumbasm.py at its final address.
"""
import struct
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
import thumbasm  # noqa: E402

OV36_BASE = 0x0217F640

LAYOUT = 0x021D0088        # 7 modes x 7 u32 item ids (slot 6 = bottom bar)
NAV = 0x021CFFA4           # 3 tables (4/5/6 items) x 8 slots x (up, down, left, right)
LABEL_POS = 0x021CFE68     # per slot (tile x, tile y) of the label window
STR_ID = 0x021CFE84        # per item: message index in bank 38
TOUCH_TABLE_NEW = 0x021D54F4   # free (assert filename strings), 36 bytes
USED_FREE_END = TOUCH_TABLE_NEW + 36 + 28

ITEM_PC = 9                # unused vanilla item id (had a spare Pokedex-style icon)
PC_MODES = (0, 2)          # normal overworld menu, and before the Pokedex
MSG_PC_LABEL = 20          # appended to bank 38


def u32(*v):
    return struct.pack('<%dI' % len(v), *v)


def edits():
    e = []
    # --- closing the menu for the PC (no app runs) must restore the top screen like a
    #     cancel does: call FieldMenu_RestoreTopScreen (0x02198530) for item PC too
    restore = TOUCH_TABLE_NEW + 36
    e.append((restore, None, thumbasm.assemble('''
        push {r3, lr}
        adds r1, r0, #0
        ldr r0, [r1, #40]           @ 1 = menu was cancelled
        cmp r0, #1
        beq 1f
        ldr r0, [r1, #48]           @ chosen item
        cmp r0, #%d
        bne 2f
1:      ldr r0, [r1, #8]
        ldrh r1, [r1, #0]
        bl 0x02198530
2:      pop {r3, pc}
''' % ITEM_PC, restore)))
    e.append((0x0219FBCC, bytes.fromhex('fff7e2ff'), thumbasm.assemble('bl 0x%X' % restore, 0x0219FBCC)))
    # --- layout: PC in slot 6 for the normal modes
    for m in PC_MODES:
        e.append((LAYOUT + m * 28 + 24, u32(0), u32(ITEM_PC)))

    # --- item count (selects the D-pad navigation table): only slots 0-5 count now
    e.append((0x021A0280, None, thumbasm.assemble('''
        movs r3, #28
        muls r0, r3
        ldr r3, =0x021D0088
        adds r3, r3, r0
        movs r0, #0
        movs r1, #0
1:      lsls r2, r1, #2
        ldr r2, [r3, r2]
        cmp r2, #0
        beq 3f
        cmp r2, #7
        beq 2f
        adds r0, #1
2:      adds r1, #1
        cmp r1, #6
        blt 1b
3:      bx lr
        .pool
''', 0x021A0280)))

    # --- slot 6 position: left half of the bottom bar, and load its icon like other slots
    e.append((0x021A03E2, None, thumbasm.assemble('''
        add r1, sp, #36
        movs r0, #64
        strb r0, [r1, #4]
        movs r0, #180
        strb r0, [r1, #5]
        b 0x021A0378
''', 0x021A03E2)))
    e.append((LABEL_POS + 12, bytes([13, 21]), bytes([6, 21])))
    e.append((STR_ID + 2 * ITEM_PC, struct.pack('<H', 0), struct.pack('<H', MSG_PC_LABEL)))

    # --- one more sprite (the PC icon) in the menu's cell-actor unit
    e.append((0x021A00D8, bytes.fromhex('0820'), bytes.fromhex('0920')))   # movs r0, #9

    # --- touch: 8 rects (6 buttons, PC, close X) + terminator, copied to a 36-byte stack buffer
    rects = [(24, 64, 8, 120), (24, 64, 136, 248), (72, 112, 8, 120), (72, 112, 136, 248),
             (120, 160, 8, 120), (120, 160, 136, 248), (168, 191, 8, 120), (168, 191, 224, 248),
             (255, 0, 0, 0)]
    e.append((TOUCH_TABLE_NEW, None, b''.join(bytes(r) for r in rects)))
    e.append((0x021A0788, u32(0x021CFF84), u32(TOUCH_TABLE_NEW)))
    e.append((0x021A070A, bytes.fromhex('88b0'), bytes.fromhex('89b0')))   # sub sp, #36
    e.append((0x021A0712, bytes.fromhex('2021'), bytes.fromhex('2421')))   # movs r1, #36
    e.append((0x021A0760, bytes.fromhex('062c'), bytes.fromhex('072c')))   # close = rect 7
    e.append((0x021A076C, bytes.fromhex('08b0'), bytes.fromhex('09b0')))   # add sp, #36
    e.append((0x021A0782, bytes.fromhex('08b0'), bytes.fromhex('09b0')))   # add sp, #36

    # --- deciding on row 3 (the bottom bar) used to mean "close"; now only the X does
    e.append((0x0219FDA2, bytes.fromhex('0329'), bytes.fromhex('ff29')))   # cmp r1, #3 -> #255

    # --- bottom bar (BG0, drawn over the buttons): only copy its right half (with the X)
    #     so the left half shows the PC button drawn in the button tilemap (gfx.py)
    e.append((0x021A0A2C, bytes.fromhex('0021'), bytes.fromhex('1021')))   # x = srcX = 16
    e.append((0x021A0A38, bytes.fromhex('2023049318200590'),
             thumbasm.assemble('''
        movs r3, #32
        str r3, [sp, #16]           @ source width (row stride) 32
        str r3, [sp, #20]           @ source height (only bounds-checked)
        lsrs r3, r3, #1             @ width 16
''', 0x021A0A38)))

    # --- D-pad: slot 6 is a normal cell (column 0, row 3)
    e.append((0x021A05CE, bytes.fromhex('062a'), bytes.fromhex('fd2a')))   # cmp r2, #6 -> never
    def nav(count, slot, dirs):
        return (NAV + (count - 4) * 32 + slot * 4, None, bytes(dirs))
    e.append(nav(6, 4, [2, 6, 4, 5]))
    e.append(nav(6, 5, [3, 6, 4, 5]))
    e.append(nav(6, 6, [255, 6, 6, 6]))
    e.append(nav(5, 4, [2, 6, 4, 4]))
    e.append(nav(5, 6, [4, 6, 6, 6]))
    return e
