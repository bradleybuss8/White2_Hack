import os, sys, struct
import ndspy.rom, ndspy.codeCompression as cc
rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1]); out=sys.argv[2]
os.makedirs(out+'/overlay', exist_ok=True)
a9 = rom.arm9
ram = rom.arm9RamAddress
ptr = rom.arm9CodeSettingsPointerAddress - ram
print('arm9 len', hex(len(a9)), 'ram', hex(ram), 'settingsptr', hex(rom.arm9CodeSettingsPointerAddress))
# module params: autoload list start, end, autoload start, bss start, bss end, compressed static end
p = struct.unpack_from('<8I', a9, ptr)
print([hex(x) for x in p])
cend = p[5]
if cend:
    dec = cc.decompress(a9[:cend-ram]) + a9[cend-ram:]
else:
    dec = a9
open(out+'/arm9.bin','wb').write(dec)
print('arm9 dec', hex(len(dec)))
open(out+'/arm9_raw.bin','wb').write(a9)
ovt = rom.loadArm9Overlays()
with open(out+'/overlays.txt','w') as f:
    for i in sorted(ovt):
        ov=ovt[i]
        open(f'{out}/overlay/ov{i:03d}.bin','wb').write(ov.data)
        f.write(f'{i:3d} ram=0x{ov.ramAddress:08X} size=0x{len(ov.data):X} bss=0x{ov.bssSize:X} file={ov.fileID} comp={ov.compressed}\n')
for fid,data in enumerate(rom.files):
    name = rom.filenames.filenameOf(fid) or f'_unnamed/{fid:05d}.bin'
    path=os.path.join(out,'files',name); os.makedirs(os.path.dirname(path),exist_ok=True)
    open(path,'wb').write(data)
