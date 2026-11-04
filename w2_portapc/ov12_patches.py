"""Overlay 12 edits (field event system and script commands).

* Field menu: selecting the PC item reserves the Porta-PC script and closes the menu
  the normal way; the field runs a reserved script as soon as it is idle again.
* Script command 0x7 (DebugStack, a no-op debug command no retail script uses) becomes
  SetPartyStatus slot, status: writes a party Pokemon's status condition.
* Script command 0x116 (PokePartyHasMoveAny, used by the Cut/Strength/Waterfall/Dive
  field scripts): if nobody knows the move and it is one of those four, the first
  non-Egg party Pokemon is returned instead of "none" (6). Surf and Fly keep the
  vanilla rules.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import thumbasm  # noqa: E402
from syms import *  # noqa: E402,F401,F403
import syms  # noqa: E402

CMD_SET_STATUS = 0x7
CMD_HAS_MOVE_ANY = 0x116
FIELD_MOVES_ANYONE = (15, 70, 127, 291)   # Cut, Strength, Waterfall, Dive
PF_STATUS = 0x9D
PF_IS_EGG = 0x4C


def build(portapc_script_id, item_pc):
    """Returns (edits, free_bytes_used). Edits are (addr, expected_or_None, new)."""
    sy = {k: v for k, v in vars(syms).items() if isinstance(v, int)}
    free = syms.OV12_FREE[0]
    blobs = []

    def place(src):
        nonlocal free
        free = (free + 3) & ~3
        code = thumbasm.assemble(src, free, sy)
        addr = free
        blobs.append((addr, None, code))
        free += len(code)
        return addr

    menu_select = place('''
        push {r4, lr}
        adds r4, r1, #0
        cmp r0, #%d
        beq 1f
        bl FieldMenu_ItemToAppIndex
        str r0, [r4, #44]
        movs r0, #5                 @ -> run the app for this item
        pop {r4, pc}
1:      ldr r0, [r4, #8]            @ GameSystem
        bl GSYS_GetGameData
        bl GameData_GetFieldStatus
        ldr r1, =%d
        bl FieldStatus_ReserveScript
        movs r0, #3                 @ -> close the menu (FieldMenuReturn event)
        pop {r4, pc}
        .pool
''' % (item_pc, portapc_script_id))

    set_status = place('''
        push {r3-r7, lr}
        adds r4, r0, #0
        adds r5, r1, #0
        bl ScriptReadAny
        adds r6, r0, #0             @ party slot
        adds r0, r4, #0
        adds r1, r5, #0
        bl ScriptReadAny
        adds r7, r0, #0             @ status condition
        adds r0, r5, #0
        bl FieldScriptEnv_GetGameData
        bl GameData_GetParty
        adds r1, r6, #0
        bl PokeParty_GetPkm
        movs r1, #%d
        adds r2, r7, #0
        bl PokeParty_SetParam
        movs r0, #0
        pop {r3-r7, pc}
''' % PF_STATUS)

    has_move_any = place('''
        push {r3-r7, lr}
        adds r5, r1, #0             @ env
        adds r4, r0, #0             @ vm
        adds r0, r5, #0
        bl FieldScriptEnv_GetGameData
        bl GameData_GetParty
        adds r6, r0, #0             @ party
        adds r0, r4, #0
        adds r1, r5, #0
        bl ScriptReadVar
        str r0, [sp, #0]            @ result variable
        adds r0, r4, #0
        adds r1, r5, #0
        bl ScriptReadAny
        adds r7, r0, #0             @ move
        movs r5, #0                 @ pass 0: knows the move; pass 1: any non-Egg
2:      movs r4, #0
3:      adds r0, r6, #0
        bl PokeParty_GetPkmCount
        cmp r4, r0
        bge 6f
        adds r0, r6, #0
        adds r1, r4, #0
        bl PokeParty_GetPkm
        cmp r5, #0
        bne 4f
        adds r1, r7, #0
        bl CheckPokeMoveLearned_NonEgg
        cmp r0, #1
        beq 9f
        b 5f
4:      movs r1, #%d
        movs r2, #0
        bl PokeParty_GetParam
        cmp r0, #0
        beq 9f
5:      adds r4, #1
        b 3b
6:      cmp r5, #0
        bne 8f
        adr r0, 7f
        movs r1, #0
10:     lsls r2, r1, #1
        ldrh r2, [r0, r2]
        cmp r2, #0
        beq 8f
        adds r1, #1
        cmp r2, r7
        bne 10b
        movs r5, #1
        b 2b
        .balign 4
7:      .hword %s, 0
8:      movs r4, #6
9:      ldr r0, [sp, #0]
        strh r4, [r0]
        movs r0, #0
        pop {r3-r7, pc}
''' % (PF_IS_EGG, ', '.join(map(str, FIELD_MOVES_ANYONE))))

    if free > syms.OV12_FREE[1]:
        raise ValueError('overlay 12 free space overflow: 0x%X' % free)

    e = list(blobs)
    # EventFieldMenu_Callback state 2 (item chosen): r5 = item, r4 = event work
    hook = thumbasm.assemble('''
        adds r0, r5, #0
        adds r1, r4, #0
        bl 0x%X
        nop
''' % menu_select, 0x0215A978)
    e.append((0x0215A978, bytes.fromhex('281c00f095f8e0620520'), hook))
    tbl = syms.EVCMD_TABLE
    e.append((tbl + 4 * CMD_SET_STATUS, struct.pack('<I', 0x02154241), struct.pack('<I', set_status | 1)))
    e.append((tbl + 4 * CMD_HAS_MOVE_ANY, struct.pack('<I', 0x021568A1), struct.pack('<I', has_move_any | 1)))
    return e, free - syms.OV12_FREE[0]
