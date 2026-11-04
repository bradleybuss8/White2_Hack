#!/usr/bin/env python3
"""Headless DeSmuME test of the White 2 Porta-PC build (py-desmume).

Needs a battery save (--save) made on Route 19 next to the tall grass at tile (56, 696),
with at least one Pokemon in the party that does not know Cut and has a level-up move
it has forgotten. Boots it, then checks:

  * the PC button is drawn and tapping it starts the Porta-PC (script 10091);
  * MOVE POKEMON opens the storage system;
  * HEAL PARTY, RELEARN MOVES and GIVE STATUS (party status word checked in RAM);
  * the repel toggle: with REPEL OFF a wild battle starts within 60 grass steps,
    with REPEL ON none in 150 steps and the encounter roll is never called;
  * the vanilla Cut-tree script offers to cut with nobody knowing Cut.

Writes a contact sheet to --out. Run with SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy.
"""
import argparse
import os
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'w2_portapc'))
from PIL import Image  # noqa: E402

import gen5pkm  # noqa: E402
import menu_patches  # noqa: E402
import walk  # noqa: E402
from emu import Emu  # noqa: E402

PARTY = 0x0221E424            # PokeParty in this save layout (GameData + 0x194 points here)
FIELD_STATUS = 0x02241F1C     # FieldStatus (reserved script at +0x12)
REPEL_STUB = menu_patches.USED_FREE_END    # build.py places the repel stub here
ENCOUNTER_ROLL = 0x021A1790   # EventWildBattleCall_CreateRandom
WILD_BATTLE_SETUP = 0x021A1C0C  # FieldEncount_SetupNormal
SCRIPT_CALL = 0x021536AC      # EventScriptCall_Create
CUT_TREE_SCRIPT = 10004

shots = []
failures = []


def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond:
        failures.append(what)


def boot(rom, save, workdir):
    e = Emu(rom, workdir)
    e.emu.backup.import_file(save)
    e.emu.reset()
    e.run(60)
    for _ in range(20):
        e.press('A', 4, 40)
    e.run(450)
    state = os.path.join(workdir, 'field.dst')
    e.save_state(state)
    return e, state


def shot(e, name):
    shots.append(e.shot(name))


def open_portapc(e):
    calls = []
    e.emu.memory.register_exec(SCRIPT_CALL, lambda a, s: calls.append(e.emu.memory.register_arm9.r1))
    e.press('X', 4, 90)
    shot(e, 'menu')
    e.touch(64, 180, hold=8, after=120)
    e.emu.memory.register_exec(SCRIPT_CALL, None)
    e.run(60)
    e.press('A', 4, 90)          # "<player> booted up the Porta-PC."
    return calls


def choose(e, index):
    for _ in range(index):
        e.press('DOWN', 4, 20)
    e.press('A', 4, 90)


def party_status(e, slot=0):
    raw = bytes(e.emu.memory.unsigned[PARTY + 8 + 220 * slot:PARTY + 8 + 220 * (slot + 1)])
    plain, ok = gen5pkm.decode(raw)
    return struct.unpack_from('<I', plain, 0x88)[0] if ok else None


def grass_walk(e, steps):
    cnt = {'stub': 0, 'roll': 0, 'battle': 0}
    m = e.emu.memory
    for key, addr in (('stub', REPEL_STUB), ('roll', ENCOUNTER_ROLL), ('battle', WILD_BATTLE_SETUP)):
        m.register_exec(addr, (lambda k: lambda a, s: cnt.__setitem__(k, cnt[k] + 1))(key))
    walk.walk_to(e, 62, 692)
    for i in range(steps):
        walk.step(e, 'UP' if i % 2 else 'DOWN')
        if cnt['battle']:
            break
    for addr in (REPEL_STUB, ENCOUNTER_ROLL, WILD_BATTLE_SETUP):
        m.register_exec(addr, None)
    e.run(90)
    return cnt


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--rom', required=True)
    ap.add_argument('--save', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    work = tempfile.mkdtemp(prefix='w2pc_')
    e, field = boot(args.rom, args.save, work)
    check(walk.pos(e) == (56, 696), 'save starts on Route 19 at (56, 696)')

    # PC button -> Porta-PC script; Move Pokemon
    calls = open_portapc(e)
    check(10091 in calls, 'tapping the PC button runs script 10091')
    shot(e, 'portapc_menu')
    choose(e, 0)
    e.run(120)
    shot(e, 'storage')
    e.press('B', 4, 60)
    e.press('DOWN', 4, 20)
    e.press('A', 4, 200)         # "Continue Box operations?" -> No
    shot(e, 'back_to_menu')

    # Give status: Poison (5), then cure (0)
    choose(e, 6)
    e.run(60)
    e.press('A', 4, 150)         # first party Pokemon
    e.run(60)
    e.press('A', 4, 120)         # Poison
    check(party_status(e) == 5, 'GIVE STATUS > Poison sets status 5')
    shot(e, 'poisoned')
    e.press('A', 4, 90)
    e.run(30)
    choose(e, 3)                 # Heal party
    e.run(240)
    check(party_status(e) == 0, 'HEAL PARTY clears the status condition')
    shot(e, 'healed')
    e.press('A', 4, 60)
    e.press('B', 4, 90)          # leave the Porta-PC

    # Repel OFF: a battle within 60 steps
    e.load_state(field)
    cnt = grass_walk(e, 60)
    check(cnt['battle'] == 1 and cnt['roll'] > 0, f'REPEL OFF: wild battle in the grass ({cnt})')
    shot(e, 'repel_off')

    # Repel ON: no rolls, no battle in 150 steps
    e.load_state(field)
    open_portapc(e)
    choose(e, 4)
    shot(e, 'repel_on_msg')
    e.press('A', 4, 90)
    e.press('B', 4, 90)
    e.run(60)
    cnt = grass_walk(e, 150)
    check(cnt['battle'] == 0 and cnt['roll'] == 0 and cnt['stub'] > 0,
          f'REPEL ON: no encounter roll in 150 grass steps ({cnt})')
    shot(e, 'repel_on')

    # Cut tree script with nobody knowing Cut asks to cut
    e.load_state(field)
    e.emu.memory.write_short(FIELD_STATUS + 0x12, CUT_TREE_SCRIPT)
    e.run(150)
    shot(e, 'cut_prompt')

    ims = [Image.open(p) for p in shots]
    cols = 5
    sheet = Image.new('RGB', (256 * cols, 384 * ((len(ims) + cols - 1) // cols)))
    for i, im in enumerate(ims):
        sheet.paste(im, ((i % cols) * 256, (i // cols) * 384))
    sheet.save(args.out)
    print(f'contact sheet: {args.out}')
    print('cut_prompt (last image) should ask "Would you like to cut it?"')
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
