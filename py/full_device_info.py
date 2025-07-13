import ctypes
import fcntl
import os
import sys
import struct

SG_IO = 0x2285
SG_DXFER_FROM_DEV = -3
SENSE_BUFFER_LEN = 32
BLOCK_SIZE = 512

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

def sg_inquiry(fd, evpd=0, page=0x00, alloc_len=96):
    cdb = (ctypes.c_ubyte * 6)(0x12, evpd, page, 0, alloc_len)
    data = (ctypes.c_ubyte * alloc_len)()
    sense = (ctypes.c_ubyte * SENSE_BUFFER_LEN)()
    hdr = sg_io_hdr()
    hdr.interface_id = ord('S')
    hdr.dxfer_direction = SG_DXFER_FROM_DEV
    hdr.cmd_len = 6
    hdr.mx_sb_len = SENSE_BUFFER_LEN
    hdr.dxfer_len = alloc_len
    hdr.dxferp = ctypes.cast(data, ctypes.c_void_p)
    hdr.cmdp = ctypes.cast(cdb, ctypes.c_void_p)
    hdr.sbp = ctypes.cast(sense, ctypes.c_void_p)
    hdr.timeout = 5000

    fcntl.ioctl(fd, SG_IO, hdr)
    if hdr.status != 0:
        return None
    return bytes(data)

def get_serial(fd):
    result = sg_inquiry(fd, evpd=1, page=0x80)
    if result and len(result) > 4:
        length = result[3]
        return result[4:4+length].decode("ascii", errors="ignore").strip()
    return None

def get_supported_VPD(fd):
    result = sg_inquiry(fd, evpd=1, page=0x00)
    if result and len(result) > 4:
        length = result[3]
        return result[4:4+length].decode("ascii", errors="ignore").strip()
    return None

def get_std_inquiry(fd):
    result = sg_inquiry(fd, evpd=0, page=0x00)
    if result and len(result) >= 36:
        vendor = result[8:16].decode("ascii", errors="ignore").strip()
        product = result[16:32].decode("ascii", errors="ignore").strip()
        revision = result[32:36].decode("ascii", errors="ignore").strip()
        return vendor, product, revision
    return None, None, None

def get_supported_sanitize(fd):
    # INQUIRY VPD page 0xB4 — supported sanitize commands
    result = sg_inquiry(fd, evpd=1, page=0xB4, alloc_len=64)
    if not result or len(result) < 6:
        return []
    support_byte = result[5]
    return [
        ("Crypto Erase", bool(support_byte & 0x01)),
        ("Block Erase", bool(support_byte & 0x02)),
        ("Overwrite", bool(support_byte & 0x04)),
    ]

def read_blocks(device_path, block_size=512, count=10):
    print(f"\nReading first {count} blocks ({block_size * count} bytes) from {device_path}...\n")
    with open(device_path, "rb") as f:
        data = f.read(block_size * count)
        for i in range(0, len(data), block_size):
            block = data[i:i+block_size]
            print(f"Block {i//block_size:03}:", block[:64].hex(), "...")  # Print only first 64 bytes for brevity

def read_block(fd, lba, num_blocks=1):
    cdb = (ctypes.c_ubyte * 10)(
        0x28,              # READ(10)
        0,                 # flags
        (lba >> 24) & 0xFF,
        (lba >> 16) & 0xFF,
        (lba >> 8) & 0xFF,
        lba & 0xFF,
        0,                 # group number
        (num_blocks >> 8) & 0xFF,
        num_blocks & 0xFF,
        0                  # control
    )

    data_len = BLOCK_SIZE * num_blocks
    data_buf = (ctypes.c_ubyte * data_len)()
    sense_buf = (ctypes.c_ubyte * SENSE_BUFFER_LEN)()

    hdr = sg_io_hdr()
    hdr.interface_id = ord('S')
    hdr.dxfer_direction = SG_DXFER_FROM_DEV
    hdr.cmd_len = 10
    hdr.mx_sb_len = SENSE_BUFFER_LEN
    hdr.dxfer_len = data_len
    hdr.dxferp = ctypes.cast(data_buf, ctypes.c_void_p)
    hdr.cmdp = ctypes.cast(cdb, ctypes.c_void_p)
    hdr.sbp = ctypes.cast(sense_buf, ctypes.c_void_p)
    hdr.timeout = 5000  # milliseconds

    try:
        fcntl.ioctl(fd, SG_IO, hdr)
        if hdr.status == 0:
            return bytes(data_buf)
        else:
            return None
    except Exception as e:
        print(f"IO error on LBA {lba}: {e}")
        return None

def main():
    device = sys.argv[1] if len(sys.argv) > 1 else "/dev/sda"
    try:
        fd = os.open(device, os.O_RDONLY)
    except PermissionError:
        print("Permission denied. Run with sudo.")
        return
    except Exception as e:
        print(f"Failed to open device {device}: {e}")
        return

    vendor, part_number, revision = get_std_inquiry(fd)
    serial = get_serial(fd)
    sanitize_support = get_supported_sanitize(fd)

    print(f"Device: {device}")
    print(f"Vendor     : {vendor}")
    print(f"Part Number: {part_number}")
    print(f"Revision   : {revision}")
    print(f"Serial No. : {serial}")
    print("Sanitize Support:")
    for feature, supported in sanitize_support:
        print(f"  {feature}: {'Yes' if supported else 'No'}")
    
    VPD_supported = get_supported_VPD(fd)
    print(f"Supported VPD: {VPD_supported if VPD_supported else 'None'}")
    
    print(f"Reading 10 blocks from {device} (one block per LBA 0-9):\n")

    for lba in range(10):
        data = read_block(fd, lba)
        if data:
            print(f"LBA {lba:03}: {data[:64].hex()} ...")  # First 64 bytes for display
        else:
            print(f"LBA {lba:03}: Read failed")
    os.close(fd)

    # Read first 100 blocks (raw)
    read_blocks(device)

if __name__ == "__main__":
    main()
