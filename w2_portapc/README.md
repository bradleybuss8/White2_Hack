# Porta-PC + QoL for Pokémon White 2 (US)

Port of the [HeartGold Porta-PC](https://github.com/bradleybuss8/Pokemon_Platinum_Patch_MASTER/tree/hg-portapc/hg_portapc)
to vanilla Pokémon White 2 (`IRDO`, "Pokemon - White Version 2 (USA, Europe) (NDSi Enhanced)",
SHA-1 `b5d7490be7b415b8f1e672a53e978a9cc667e56a`).

## What it does

The X menu (touch screen) gets a **PC** button on the left of its bottom bar, next to
the close X. Tap it, or move the cursor down from SAVE/OPTIONS and press A. It opens
the Porta-PC menu:

| Option | Effect |
| --- | --- |
| Move Pokémon / Move items / Battle Box | open the storage system in that mode, then return to the menu |
| Heal party | fade out, heal sound, fully restores HP/PP/status |
| Repel: OFF / Repel: ON | turn walking/surfing wild encounters off or on; the item shows the current state |
| Relearn moves | free Move Reminder: pick a party Pokémon, choose any level-up move it could know |
| Give status | pick a party Pokémon, then Poison, Burn, Paralysis, Sleep, Freeze or Cure (Eggs are refused) |
| See ya! (or B) | close the Porta-PC |

Differences from the HeartGold version:

* **Battle Box** is listed, since the White 2 PC has one.
* **Give status** has no Toxic. In Gen 5 a party Pokémon's status is one of
  paralysis/sleep/freeze/burn/poison, and "badly poisoned" turns into regular poison after
  every battle, so there is nothing to set.
* The **PC button** sits on the bottom bar. The X menu is a 2×3 grid of large buttons
  with no free cell, so the PC uses the left half of the bar; the X stays on the right.

**Repel toggle.** While it is ON, no wild Pokémon appear when walking in grass or caves
or when surfing. Fishing, Sweet Scent, rustling grass / dust clouds / ripples, Hidden
Grottoes and scripted encounters still work. The setting is event flag 550 (unused in
vanilla: no script, NPC or trainer uses flags 498-603), so it is saved.

Rules, as in the HeartGold version:

* The button shows once you have a Pokémon (it is in the normal menu, and in the
  menu before you get the Pokédex), and the script does nothing with an empty party.
* It is not in the Union Room, the Royal Unova, the Black Tower / White Treehollow
  or the season-change menu, which use their own layouts.

## QoL changes

| Change | Details |
| --- | --- |
| Field moves without the HM | Cut, Strength, Waterfall and Dive work when nobody in the party knows the move; your first non-Egg Pokémon does it. Surf and Fly keep the vanilla rules. |
| No trade evolutions | Every trade evolution happens by level instead (table below). |

| Pokémon | Evolves into | New method |
| --- | --- | --- |
| Kadabra, Machoke, Graveler, Haunter, Boldore, Gurdurr | Alakazam, Machamp, Golem, Gengar, Gigalith, Conkeldurr | Lv 37 |
| Poliwhirl | Politoed | Lv 37 (Water Stone still gives Poliwrath) |
| Slowpoke | Slowbro / Slowking | Lv 37: male → Slowbro, female → Slowking |
| Onix, Scyther | Steelix, Scizor | Lv 35 |
| Feebas | Milotic | Lv 35 (was Prism Scale trade; the Beauty method is kept) |
| Porygon, Karrablast, Shelmet | Porygon2, Escavalier, Accelgor | Lv 30 |
| Seadra, Porygon2 | Kingdra, Porygon-Z | Lv 45 |
| Electabuzz, Magmar, Dusclops | Electivire, Magmortar, Dusknoir | Lv 50 |
| Rhydon | Rhyperior | Lv 55 |
| Clamperl | Huntail / Gorebyss | Lv 30: male → Huntail, female → Gorebyss |

The levels are in `TRADE_EVOS` in `qol.py`.

Not ported because White 2 already has them: reusable TMs, Pokémon names in normal
case, and nature effects on the summary screen (the stats the nature raises and lowers
are colored). Flash only matters in HeartGold's dark caves.

## How it works

No decomp exists for White 2. Addresses and names come from the
[swan](https://github.com/ds-pokemon-hacking/swan) symbol database (`IRDO.yml`).
Script command arguments come from CTRMapV's Gen 5 script SDK.

* **X menu (overlay 36, `menu_patches.py`).** The menu has 7 slots per layout: 0-5 are
  the grid and slot 6 was the bottom bar, which only the close X used (as touch rect 6).
  Slot 6 now holds the new item 9, the PC, in layouts 0 and 2:
  * the item counter ignores slot 6;
  * slot 6 is positioned and its icon loaded like the other slots;
  * one more sprite in the menu's cell-actor unit;
  * a 9-entry touch table (PC = rect 6, close X = rect 7);
  * D-pad navigation to and from the bar;
  * row 3 no longer means "close" when deciding;
  * the bar (BG0) is only copied into its right half, so the PC button frame drawn in the
    button tilemap shows on the left;
  * closing the menu for the PC restores the top screen like a cancel does.
* **Running the script (overlay 12, `ov12_patches.py`).** When item 9 is chosen,
  `EventFieldMenu` calls `FieldStatus_ReserveScript(10091)` and closes the menu the
  normal way. The field runs a reserved script as soon as it is idle again.
* **Porta-PC script (`portapc_script.py`).** It is assembled by `tools/gen5script.py`
  and appended to the Pokémon Center PC's global script file (a/0/5/6 #1244, IDs
  10090-10099). Its strings go into that file's text bank (a/0/0/3 #479).
* **Script command 0x7** (DebugStack, an unused debug no-op) becomes
  `SetPartyStatus slot, status`. **Script command 0x116** (`PokePartyHasMoveAny`, used
  by the field-move scripts) is replaced by a version with the first-non-Egg fallback.
* **Repel (overlay 36, `repel_patch.py`).** `CheckCallRandomEncounter` calls a stub
  that skips `EventWildBattleCall_CreateRandom` while flag 550 is set.
* **Free space.** New code and tables use overlay bytes that held source file names
  passed only to assert / heap-debug calls. `tools/freespace.py` checks every reference
  to them before the build uses them.
* **Graphics (a/0/7/0, `gfx.py`).** The PC icon is drawn over a spare Pokédex-style icon,
  and a 3-tile-high button is added to tilemaps 18 and 20.
* **Compression and ROM layout.** Overlays are BLZ-compressed. `tools/blzpatch.py`
  re-encodes only the tokens around each edit, so the patch stays small. Grown files are
  appended after the NTR data. The DSi-only (TWL) region that followed it is moved
  further out, and its header offsets are updated (`tools/romwriter.py`). The game is
  played in DS mode; DSi-mode signature checks no longer match, as with any edited
  DSi-enhanced ROM.

## Building

Requirements: `binutils-arm-none-eabi`, Python 3 with `ndspy`, `PyYAML` and `Pillow`,
and `xdelta3`.

```sh
python3 -I w2_portapc/build.py --rom "Pokemon - White Version 2 (USA, Europe) (NDSi Enhanced).nds" \
    --out White2_PortaPC.nds
xdelta3 -e -9 -S none -B 536870912 -s "Pokemon - White Version 2 (USA, Europe) (NDSi Enhanced).nds" \
    White2_PortaPC.nds White2_PortaPC.xdelta
```

The build refuses anything but the clean ROM above. It stops if any patched byte isn't
the vanilla value it expects, or if the free space is referenced by anything other than
assert/heap-debug calls. Output SHA-1: `f1f7410557854e746d4102b4e2b01607f6b3287a`.

## Applying the patch

Apply `patch/White2_PortaPC.xdelta` to the clean ROM with any xdelta patcher (xdelta3,
Delta Patcher, or Rom Patcher JS). Existing saves work as-is.

## Testing

`tools/portapc_test.py` drives the ROM headlessly with py-desmume. It needs a battery
save on Route 19 at tile (56, 696), next to the first tall grass, with a party Pokémon
that doesn't know Cut.

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 -I tools/portapc_test.py \
    --rom White2_PortaPC.nds --save route19.sav --out sheet.png
```

It checks:

* the PC button runs script 10091;
* Move Pokémon opens storage;
* Give Status > Poison sets the party status, and Heal Party clears it;
* Repel OFF: a wild battle starts in the grass. Repel ON: no encounter roll in 150 steps;
* the vanilla Cut-tree script offers to cut with nobody knowing Cut.

Relearn Moves and the pre-Pokédex menu layout were checked by hand in the emulator.

Not covered: the trade-evolution changes (the build checks each replaced entry against
vanilla, and the method numbers match vanilla data such as Burmy's), Strength,
Waterfall and Dive (same command as Cut), and surfing with the repel on (same check
as walking).
