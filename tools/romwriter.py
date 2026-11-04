"""Write changed files into an NDS ROM image without repacking it.

Unchanged files keep their offsets, so an xdelta against the original stays small.
Files that no longer fit in their old slot are appended after the end of the NTR
(DS-mode) data. On DSi-enhanced ROMs (Black 2 / White 2) the TWL (DSi-mode) region
starts right there, so if the appended files reach it, the whole TWL block is moved
past them and the header offsets that point into it are updated. DS mode only reads
the NTR region, which must end before the TWL region (reads past it fail).
"""
import struct

ALIGN = 0x200
TWL_UNIT = 0x80000          # header 0x90/0x92 count in 512 KiB units
# header fields holding ROM offsets inside the TWL region
TWL_OFFSET_FIELDS = (0x1C0, 0x1D0, 0x1E8, 0x220, 0x228)


def crc16(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


class RomImage:
    def __init__(self, data):
        self.buf = bytearray(data)
        self.fat_off, self.fat_size = struct.unpack_from('<II', self.buf, 0x48)
        self.tail = (struct.unpack_from('<I', self.buf, 0x80)[0] + ALIGN - 1) & ~(ALIGN - 1)
        self.twl = None
        if self.buf[0x12] & 2:      # unit code: DSi enhanced / exclusive
            start = struct.unpack_from('<H', self.buf, 0x92)[0] * TWL_UNIT
            end = struct.unpack_from('<I', self.buf, 0x210)[0]
            if start:
                self.twl = (start, bytes(self.buf[start:end]))

    def _alloc(self, size):
        off = self.tail
        limit = len(self.buf) - (len(self.twl[1]) + TWL_UNIT if self.twl else 0)
        if off + size > limit:
            raise ValueError('no free space left in the ROM image')
        self.tail = (off + size + ALIGN - 1) & ~(ALIGN - 1)
        return off

    def _place(self, old_off, old_cap, data):
        """Write data at old_off if it fits in old_cap bytes, else append. Returns offset."""
        if len(data) <= old_cap:
            off = old_off
            self.buf[off:off + old_cap] = b'\xFF' * old_cap
        else:
            off = self._alloc(len(data))
        self.buf[off:off + len(data)] = data
        return off

    def set_file(self, fid, data):
        start, end = struct.unpack_from('<II', self.buf, self.fat_off + 8 * fid)
        off = self._place(start, end - start, data)
        struct.pack_into('<II', self.buf, self.fat_off + 8 * fid, off, off + len(data))

    def set_arm9_overlay_table(self, table):
        off, size = struct.unpack_from('<II', self.buf, 0x50)
        if len(table) != size:
            raise ValueError('overlay table size changed')
        self.buf[off:off + size] = table

    def _move_twl(self):
        start, blob = self.twl
        if self.tail <= start:
            return
        new = (self.tail + TWL_UNIT - 1) & ~(TWL_UNIT - 1)
        delta = new - start
        self.buf[new:new + len(blob)] = blob
        units = new // TWL_UNIT
        struct.pack_into('<HH', self.buf, 0x90, units, units)
        for f in TWL_OFFSET_FIELDS:
            v = struct.unpack_from('<I', self.buf, f)[0]
            if v >= start:
                struct.pack_into('<I', self.buf, f, v + delta)
        struct.pack_into('<I', self.buf, 0x210, struct.unpack_from('<I', self.buf, 0x210)[0] + delta)

    def finish(self):
        used = max(struct.unpack_from('<I', self.buf, 0x80)[0], self.tail)
        struct.pack_into('<I', self.buf, 0x80, used)
        if self.twl:
            self._move_twl()
        struct.pack_into('<H', self.buf, 0x15E, crc16(self.buf[:0x15E]))
        return bytes(self.buf)
