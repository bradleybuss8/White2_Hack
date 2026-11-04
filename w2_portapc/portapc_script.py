"""The Porta-PC field script (global script 10091, in the Pokemon Center PC's script
file, so it shares that file's text bank 479).

Menu: MOVE POKEMON / MOVE ITEMS / BATTLE BOX / HEAL PARTY / REPEL: ON-OFF /
RELEARN MOVES / GIVE STATUS / SEE YA!. Does nothing when the party is empty.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from gen5script import Script, EQ  # noqa: E402

SCRIPT_FILE = 1244          # a/0/5/6 member: global scripts 10090-10099
SCRIPT_FIRST_ID = 10090
TEXT_BANK = 479             # a/0/0/3 member used by that script file

# vanilla strings in bank 479
MSG_MOVE_MON, MSG_MOVE_ITEMS, MSG_BATTLE_BOX = 17, 18, 20
MSG_MOVE_MON_DESC, MSG_MOVE_ITEMS_DESC, MSG_BATTLE_BOX_DESC = 23, 24, 26
SE_PC_ACCESS = 1372
SE_HEAL = 1391
SE_SELECT = 1351

# new strings, appended to bank 479 in this order
TEXTS = [
    ('BOOTED', '{PLAYER} booted up the Porta-PC.'),
    ('PROMPT', 'What would you like to do?'),
    ('HEAL', 'Heal party'),
    ('HEAL_DESC', 'Fully restore the HP, PP, and status\\nof the Pokémon in your party.'),
    ('HEALED', 'Your Pokémon were restored\\nto full health!'),
    ('REPEL_ON', 'Repel: ON'),
    ('REPEL_OFF', 'Repel: OFF'),
    ('REPEL_DESC', 'Turn wild Pokémon encounters\\nin grass, caves, and water on or off.'),
    ('REPEL_ON_MSG', 'Wild Pokémon won’t appear now.'),
    ('REPEL_OFF_MSG', 'Wild Pokémon will appear again.'),
    ('RELEARN', 'Relearn moves'),
    ('RELEARN_DESC', 'Remember a move your Pokémon\\nforgot or never learned.'),
    ('NO_MOVES', 'There are no moves {MON0}\\ncan remember.'),
    ('EGG', 'An Egg can’t do that.'),
    ('STATUS', 'Give status'),
    ('STATUS_DESC', 'Give or cure a status condition\\non a Pokémon in your party.'),
    ('STATUS_WHICH', 'Which condition should\\n{MON0} have?'),
    ('ST_POISON', 'Poison'),
    ('ST_BURN', 'Burn'),
    ('ST_PARALYSIS', 'Paralysis'),
    ('ST_SLEEP', 'Sleep'),
    ('ST_FREEZE', 'Freeze'),
    ('ST_CURE', 'Cure'),
    ('BACK', 'Back'),
    ('ST_DESC', 'Give the Pokémon this\\nstatus condition.'),
    ('ST_CURE_DESC', 'Heal the Pokémon’s\\nstatus condition.'),
    ('BACK_DESC', 'Go back to the Porta-PC menu.'),
    ('MSG_POISON', '{MON0} was poisoned!'),
    ('MSG_BURN', '{MON0} was burned!'),
    ('MSG_PARALYSIS', '{MON0} is paralyzed!'),
    ('MSG_SLEEP', '{MON0} fell asleep!'),
    ('MSG_FREEZE', '{MON0} was frozen solid!'),
    ('MSG_CURE', '{MON0}’s status condition\\nwas healed!'),
    ('SEE_YA', 'See ya!'),
    ('SEE_YA_DESC', 'Log out of the Porta-PC.'),
]

# Party status condition (Gen 5 stores an enum, not the Gen 4 bit field):
# 1 paralysis, 2 sleep, 3 freeze, 4 burn, 5 poison. Gen 5 has no out-of-battle
# "badly poisoned" (it turns into regular poison after a battle), so there is no Toxic.
STATUSES = [  # (menu text, message, value)
    ('ST_POISON', 'MSG_POISON', 5),
    ('ST_BURN', 'MSG_BURN', 4),
    ('ST_PARALYSIS', 'MSG_PARALYSIS', 1),
    ('ST_SLEEP', 'MSG_SLEEP', 2),
    ('ST_FREEZE', 'MSG_FREEZE', 3),
    ('ST_CURE', 'MSG_CURE', 0),
]

V_RESULT, V_SEL, V_TMP, V_SLOT, V_OK = 0x8000, 0x8001, 0x8002, 0x8003, 0x8004
CANCEL_B, CANCEL_X = 0xFFFE, 0xFFFD
MSG_WIN = 2   # message box type used by the vanilla PC script


def build(first_msg, repel_flag):
    m = {name: first_msg + i for i, (name, _) in enumerate(TEXTS)}
    s = Script()

    def if_eq(var, value, label):
        s.CmpVarConst(var, value)
        s.JumpIf(EQ, label)

    s.ActorPauseAll()
    s.PartyGetCount(V_RESULT, 0)
    if_eq(V_RESULT, 0, 'release')
    s.SEPlay(SE_PC_ACCESS)
    s.WordSetPlayerName(0)
    s.Msg(m['BOOTED'], MSG_WIN)
    s.WaitButton()

    s.label('menu')
    s.Msg(m['PROMPT'], MSG_WIN)
    s.ListMenuInitTR(31, 1, 0, 1, V_SEL)
    s.ListMenuAdd(MSG_MOVE_MON, MSG_MOVE_MON_DESC, 0)
    s.ListMenuAdd(MSG_MOVE_ITEMS, MSG_MOVE_ITEMS_DESC, 1)
    s.ListMenuAdd(MSG_BATTLE_BOX, MSG_BATTLE_BOX_DESC, 2)
    s.ListMenuAdd(m['HEAL'], m['HEAL_DESC'], 3)
    s.FlagGet(repel_flag, V_TMP)
    if_eq(V_TMP, 1, 'menu_repel_on')
    s.ListMenuAdd(m['REPEL_OFF'], m['REPEL_DESC'], 4)
    s.Jump('menu_rest')
    s.label('menu_repel_on')
    s.ListMenuAdd(m['REPEL_ON'], m['REPEL_DESC'], 4)
    s.label('menu_rest')
    s.ListMenuAdd(m['RELEARN'], m['RELEARN_DESC'], 5)
    s.ListMenuAdd(m['STATUS'], m['STATUS_DESC'], 6)
    s.ListMenuAdd(m['SEE_YA'], m['SEE_YA_DESC'], 7)
    s.ListMenuShow()
    s.MsgClose()
    for value, label in ((0, 'pc_move_mon'), (1, 'pc_move_items'), (2, 'pc_battle_box'),
                         (3, 'heal'), (4, 'repel'), (5, 'relearn'), (6, 'status')):
        if_eq(V_SEL, value, label)
    s.Jump('exit')

    # ---- PC storage (CallPC modes: 2 move Pokemon, 3 move items, 4 Battle Box)
    for label, mode in (('pc_move_mon', 2), ('pc_move_items', 3), ('pc_battle_box', 4)):
        s.label(label)
        s.SEPlay(SE_PC_ACCESS)
        s.FadeOutBlack()
        s.FadeWait()
        s.CallPC(V_RESULT, mode)
        s.FadeInBlack()
        s.FadeWait()
        if_eq(V_RESULT, 1, 'exit')          # the storage system was closed for good
        s.Jump('menu')

    # ---- heal
    s.label('heal')
    s.FadeOutBlack()
    s.FadeWait()
    s.PartyRecoverAll()
    s.SEPlay(SE_HEAL)
    s.SEWait()
    s.FadeInBlack()
    s.FadeWait()
    s.Msg(m['HEALED'], MSG_WIN)
    s.WaitButton()
    s.Jump('menu')

    # ---- repel toggle
    s.label('repel')
    s.FlagGet(repel_flag, V_TMP)
    if_eq(V_TMP, 1, 'repel_off')
    s.FlagSet(repel_flag)
    s.SEPlay(SE_SELECT)
    s.Msg(m['REPEL_ON_MSG'], MSG_WIN)
    s.WaitButton()
    s.Jump('menu')
    s.label('repel_off')
    s.FlagReset(repel_flag)
    s.SEPlay(SE_SELECT)
    s.Msg(m['REPEL_OFF_MSG'], MSG_WIN)
    s.WaitButton()
    s.Jump('menu')

    # ---- shared: pick a party Pokemon into V_SLOT (back to the menu if cancelled / Egg)
    s.label('pick')
    s.CallPokeSelect(0, V_OK, V_SLOT, 0)
    if_eq(V_OK, 0, 'pick_cancel')
    s.PartyIsEgg(V_TMP, V_SLOT)
    if_eq(V_TMP, 1, 'pick_egg')
    s.SetVar(V_OK, 1)
    s.Return()
    s.label('pick_egg')
    s.Msg(m['EGG'], MSG_WIN)
    s.WaitButton()
    s.label('pick_cancel')
    s.SetVar(V_OK, 0)
    s.Return()

    # ---- move reminder (free)
    s.label('relearn')
    s.Call('pick')
    if_eq(V_OK, 0, 'menu')
    s.MoveReminderCheckPkm(V_TMP, V_SLOT)
    if_eq(V_TMP, 0, 'relearn_none')
    s.MoveReminderCallMoveSelect(V_TMP, V_SLOT)
    s.Jump('menu')
    s.label('relearn_none')
    s.WordSetPartyPokeName(0, V_SLOT)
    s.Msg(m['NO_MOVES'], MSG_WIN)
    s.WaitButton()
    s.Jump('menu')

    # ---- status conditions
    s.label('status')
    s.Call('pick')
    if_eq(V_OK, 0, 'menu')
    s.WordSetPartyPokeName(0, V_SLOT)
    s.Msg(m['STATUS_WHICH'], MSG_WIN)
    s.ListMenuInitTR(31, 1, 0, 1, V_SEL)
    for i, (item, _, _) in enumerate(STATUSES):
        desc = m['ST_CURE_DESC'] if item == 'ST_CURE' else m['ST_DESC']
        s.ListMenuAdd(m[item], desc, i)
    s.ListMenuAdd(m['BACK'], m['BACK_DESC'], len(STATUSES))
    s.ListMenuShow()
    s.MsgClose()
    for i in range(len(STATUSES)):
        if_eq(V_SEL, i, 'st_%d' % i)
    s.Jump('menu')
    for i, (_, msg, value) in enumerate(STATUSES):
        s.label('st_%d' % i)
        s.SetPartyStatus(V_SLOT, value)
        s.WordSetPartyPokeName(0, V_SLOT)
        s.SEPlay(SE_SELECT)
        s.Msg(m[msg], MSG_WIN)
        s.WaitButton()
        s.Jump('menu')

    s.label('exit')
    s.MsgClose()
    s.label('release')
    s.FinishSubEvents()
    s.ActorUnlockAll()
    s.Halt()
    return s, m
