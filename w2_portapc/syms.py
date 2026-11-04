"""Addresses in Pokemon White 2 (USA, IRDO) used by the patches.

Function names follow the swan symbol database (ds-pokemon-hacking/swan, IRDO.yml).
Thumb functions have bit 0 set so the assembler emits BL to them.
"""
# ARM9
GSYS_GetGameData = 0x02016AD9
GameData_GetParty = 0x0201735D
GameData_GetEventWork = 0x02017395
GameData_GetFieldStatus = 0x020175B5
EventWork_FlagGet = 0x020191D9
FieldStatus_ReserveScript = 0x02019369
PokeParty_GetParam = 0x0201CD25
PokeParty_SetParam = 0x0201CD49
PokeParty_GetPkmCount = 0x0201FE25
PokeParty_GetPkm = 0x0201FF35

# overlay 12 (field events / script engine)
ScriptReadVar = 0x02154929
ScriptReadAny = 0x02154951
FieldScriptEnv_GetGameData = 0x021551B5
CheckPokeMoveLearned_NonEgg = 0x02156209
FieldMenu_ItemToAppIndex = 0x0215AAA9      # unnamed in swan: table lookup used by EventFieldMenu
EVCMD_TABLE = 0x0216B578

# overlay 36 (field)
EventWildBattleCall_CreateRandom = 0x021A1791

OV12_BASE = 0x02150400
OV36_BASE = 0x0217F640

# Free space: assert/heap-debug file-name strings (see tools/freespace.py)
OV12_FREE = (0x0216E1F4, 0x0216E1F4 + 296)
OV36_FREE = (0x021D54F4, 0x021D54F4 + 254)
