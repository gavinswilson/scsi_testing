import ctypes
import fcntl
import os

SG_IO = 0x2285
SG_DXFER_FROM_DEV = -3
SENSE_LEN = 32
ATA_SECTOR_SIZE = 512

class sg_io_hdr(ctypes.Structure):
    _fields_ = [
        ("interface_id", ctypes.c_int),
        ("dxfer_direction", ctypes.c_int),
        ("cmd_len", ctypes.c_ubyte),
        ("mx_sb_len", ctypes.c_ubyte),
        ("iovec_count", ctypes.c_ushort),
        ("dxfer_len", ctypes.c_uint),
        ("dxferp", ctypes.c_void_p),
        ("cmdp", ctypes.c_void_p),
        ("sbp", ctypes.c_void_p),
        ("timeout", ctypes.c_uint),
        ("flags", ctypes.c_uint),
        ("pack_id", ctypes.c_int),
        ("usr_ptr", ctypes.c_void_p),
        ("status", ctypes.c_ubyte),
        ("masked_status", ctypes.c_ubyte),
        ("msg_status", ctypes.c_ubyte),
        ("sb_len_wr", ctypes.c_ubyte),
        ("host_status", ctypes.c_ushort),
        ("driver_status", ctypes.c_ushort),
        ("resid", ctypes.c_int),
        ("duration", ctypes.c_uint),
        ("info", ctypes.c_uint),
    ]

def ata_smart_read_log(dev="/dev/sg0"):
    cdb = (ctypes.c_ubyte * 16)(
        0x85,       # ATA PASS-THROUGH(16)
        0x08,       # PIO Data-In protocol
        0x0E,       # T_DIR=IN, BYT_BLOK=1
        0x00,       # Features
        0x01,       # Sector Count (1 block)
        0x06,       # LBA Low (log addr: 0x06 = self-test)
        0x4F,       # LBA Mid
        0xC2,       # LBA High
        0x00,       # Device
        0x2F,       # Command (SMART READ LOG)
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00  # Reserved
    )

    data_buf = (ctypes.c_ubyte * ATA_SECTOR_SIZE)()
    sense_buf = (ctypes.c_ubyte * SENSE_LEN)()

    hdr = sg_io_hdr()
    hdr.interface_id = ord('S')
    hdr.dxfer_direction = SG_DXFER_FROM_DEV
    hdr.cmd_len = 16
    hdr.mx_sb_len = SENSE_LEN
    hdr.dxfer_len = ATA_SECTOR_SIZE
    hdr.dxferp = ctypes.cast(data_buf, ctypes.c_void_p)
    hdr.cmdp = ctypes.cast(cdb, ctypes.c_void_p)
    hdr.sbp = ctypes.cast(sense_buf, ctypes.c_void_p)
    hdr.timeout = 10000  # ms

    fd = os.open(dev, os.O_RDONLY)
    try:
        fcntl.ioctl(fd, SG_IO, hdr)
    finally:
        os.close(fd)

    if hdr.status != 0:
        sense = bytes(sense_buf[:hdr.sb_len_wr])
        print(f"SCSI status = {hdr.status:#x}")
        print(f"Sense data: {sense.hex()}")
        raise RuntimeError("SMART READ LOG failed")


    return bytes(data_buf)

# Parse and print self-test log
def parse_self_test_log(log_data):
    entries = []
    for i in range(0, 21):  # 21 entries in SMART log
        offset = 1 + i * 22  # skip byte 0 (log revision)
        entry = log_data[offset:offset+22]
        if len(entry) < 22 or entry[0] == 0x00:
            continue  # empty or invalid

        status = entry[0] >> 4
        type_ = entry[0] & 0x0F
        lifetime = entry[1] | (entry[2] << 8)
        print(f"Test {i}: Status={status}, Type={type_}, Lifetime={lifetime} hours")
        entries.append((i, status, type_, lifetime))
    return entries

# Run it
log = ata_smart_read_log("/dev/sg0")
parse_self_test_log(log)
