"""Overlay 36: the Porta-PC repel toggle.

CheckCallRandomEncounter (walking / surfing encounter roll) calls
EventWildBattleCall_CreateRandom(encountSystem, 0). That call is redirected to a stub
that returns "no encounter" while REPEL_FLAG is set. Fishing, Sweet Scent, rustling
grass / dust clouds and scripted encounters use other paths and are not affected.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import thumbasm  # noqa: E402
import syms  # noqa: E402

CALL_SITE = 0x02182B4C      # in CheckCallRandomEncounter


def build(addr, flag):
    sy = {k: v for k, v in vars(syms).items() if isinstance(v, int)}
    stub = thumbasm.assemble('''
        push {r4-r6, lr}
        adds r4, r0, #0
        adds r5, r1, #0
        ldr r0, [r4, #8]            @ GameData
        bl GameData_GetEventWork
        ldr r1, =%d
        bl EventWork_FlagGet
        cmp r0, #0
        bne 1f
        adds r0, r4, #0
        adds r1, r5, #0
        bl EventWildBattleCall_CreateRandom
        pop {r4-r6, pc}
1:      movs r0, #0
        pop {r4-r6, pc}
        .pool
''' % flag, addr, sy)
    call = thumbasm.assemble('bl 0x%X' % addr, CALL_SITE)
    return [(addr, None, stub), (CALL_SITE, bytes.fromhex('1ef020fe'), call)], len(stub)
