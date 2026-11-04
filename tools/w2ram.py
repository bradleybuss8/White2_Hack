EW=0x2225524
def flag_addr(f): return EW+0x35e+(f>>3), 1<<(f&7)
def set_flag(e,f,v=True):
    a,b=flag_addr(f); m=e.emu.memory; cur=m.unsigned[a]
    m.write_byte(a,(cur|b) if v else (cur&~b))
def get_flag(e,f):
    a,b=flag_addr(f); return bool(e.emu.memory.unsigned[a]&b)
def var_addr(v): return EW+(v-0x4000)*2
