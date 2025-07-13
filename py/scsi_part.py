import ctypes
import fcntl
import os
import sys

SG_IO = 0x2285
SG_DXFER_FROM_DEV = -3
INQ_REPLY_LEN = 96
SENSE_BUFFER_LEN = 32
INQ_CMD_LEN = 6

class sg_io_hdr(ctypes.Structure):
    _fields_ = [
        ('interface_id', ctypes.c_int),
        ('dxfer_direction', ctypes.c_int),
        ('cmd_len', ctypes.c_ubyte),
        ('mx_sb_len', ctypes.c_ubyte),
        ('iovec_count', ctypes.c_ushort),
        ('dxfer_len', ctypes.c_uint),
        ('dxferp', ctypes.c_void_p),
        ('cmdp', ctypes.c_void_p),
        ('sbp', ctypes.c_void_p),
        ('timeout', ctypes.c_uint),
        ('flags', ctypes.c_uint),
        ('pack_id', ctypes.c_int),
        ('usr_ptr', ctypes.c_void_p),
        ('status', ctypes.c_ubyte),
        ('masked_status', ctypes.c_ubyte),
        ('msg_status', ctypes.c_ubyte),
        ('sb_len_wr', ctypes.c_ubyte),
        ('host_status', ctypes.c_ushort),
        ('driver_status', ctypes.c_ushort),
        ('resid', ctypes.c_int),
        ('duration', ctypes.c_uint),
        ('info', ctypes.c_uint),
    ]

def get_part_number(device="/dev/sda"):
    # Standard INQUIRY: EVPD=0
    cdb = (ctypes.c_ubyte * INQ_CMD_LEN)(0x12, 0x00, 0x00, 0x00, INQ_REPLY_LEN, 0x00)
    data_buf = (ctypes.c_ubyte * INQ_REPLY_LEN)()
    sense_buf = (ctypes.c_ubyte * SENSE_BUFFER_LEN)()

    hdr = sg_io_hdr()
    hdr.interface_id = ord('S')
    hdr.dxfer_direction = SG_DXFER_FROM_DEV
    hdr.cmd_len = INQ_CMD_LEN
    hdr.mx_sb_len = SENSE_BUFFER_LEN
    hdr.dxfer_len = INQ_REPLY_LEN
    hdr.dxferp = ctypes.cast(data_buf, ctypes.c_void_p)
    hdr.cmdp = ctypes.cast(cdb, ctypes.c_void_p)
    hdr.sbp = ctypes.cast(sense_buf, ctypes.c_void_p)
    hdr.timeout = 5000  # ms

    try:
        fd = os.open(device, os.O_RDONLY)
        fcntl.ioctl(fd, SG_IO, hdr)
        os.close(fd)
    except PermissionError:
        print("Permission denied. Use sudo.")
        return
    except Exception as e:
        print(f"Device access failed: {e}")
        return

    if hdr.status != 0:
        print("SCSI command failed")
        return

    # Bytes 16–31 contain the Product ID (Part Number)
    part_number = bytes(data_buf[16:32]).decode('ascii', errors='ignore').strip()
    print(f"Part Number (Product ID): '{part_number}'")
    revision = bytes(data_buf[32:36]).decode('ascii', errors='ignore').strip()
    print(f"Revision Level: '{revision}'")
    full_data_buffer = bytes(data_buf[00:92]).decode('ascii', errors='ignore').strip()
    print(f"Full Data Buffer: '{full_data_buffer}'")

if __name__ == "__main__":
    dev = sys.argv[1] if len(sys.argv) > 1 else "/dev/sda"
    get_part_number(dev)
