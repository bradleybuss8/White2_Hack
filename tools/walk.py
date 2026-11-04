import struct
from emu import hold
PS=[0x223b484]
def find_ps(e):
    m=e.emu.memory; got=[]
    def cb(a,s): got.append(m.register_arm9.r0)
    m.register_exec(0x2017544, cb)
    for _ in range(60):
        e.run(1)
        if got: break
    m.register_exec(0x2017544, None)
    PS[0]=got[0]; return got[0]
def pos(e):
    m=e.emu.memory; p=PS[0] or find_ps(e)
    x,y,z=struct.unpack('<iii', bytes(m.unsigned[p+4:p+16]))
    return x>>16, z>>16
def step(e,d,n=1):
    hold(e,d,16*n+1,4)
def walk_to(e,tx,tz,maxsteps=80,log=None):
    stuck=0
    for i in range(maxsteps):
        x,z=pos(e)
        if (x,z)==(tx,tz): return True
        dirs=[]
        if x<tx: dirs.append('RIGHT')
        if x>tx: dirs.append('LEFT')
        if z<tz: dirs.append('DOWN')
        if z>tz: dirs.append('UP')
        if stuck: dirs=dirs[::-1]+[d for d in ('UP','LEFT','RIGHT','DOWN') if d not in dirs]
        moved=False
        for d in dirs:
            step(e,d); nx,nz=pos(e)
            if (nx,nz)!=(x,z): moved=True; break
        stuck = 0 if moved else stuck+1
        if log: log.append((x,z))
        if stuck>3: return False
    return pos(e)==(tx,tz)
