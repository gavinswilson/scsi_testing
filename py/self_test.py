import ctypes
import fcntl
import os
import time
import sys

SG_IO = 0x2285
SG_DXFER_TO_DEV = -2
SG_DXFER_FROM_DEV = -3
SENSE_BUFFER_LEN = 32
SEND_DIAG_LEN = 6
LOG_SENSE_LEN = 10
LOG_SENSE_REPLY_LEN = 512

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

def send_self_test(fd):
    # SEND DIAGNOSTIC: self-test bit = 1, self-test code = 1 (short test)
    cdb = (ctypes.c_ubyte * SEND_DIAG_LEN)(0x1D, 0x04, 0x00, 0x00, 0x00, 0x00)
    sense_buf = (ctypes.c_ubyte * SENSE_BUFFER_LEN)()
    data_buf = (ctypes.c_ubyte * LOG_SENSE_REPLY_LEN)()
    hdr = sg_io_hdr()
    hdr.interface_id = ord('S')
    hdr.dxfer_direction = SG_DXFER_TO_DEV
    hdr.cmd_len = SEND_DIAG_LEN
    hdr.mx_sb_len = SENSE_BUFFER_LEN
    hdr.dxfer_len = 0
    hdr.dxferp = ctypes.cast(data_buf, ctypes.c_void_p)
    hdr.cmdp = ctypes.cast(cdb, ctypes.c_void_p)
    hdr.sbp = ctypes.cast(sense_buf, ctypes.c_void_p)
    hdr.timeout = 10000  # ms

    fcntl.ioctl(fd, SG_IO, hdr)

    if hdr.status != 0:
        print("SEND DIAGNOSTIC command failed.")
        return False
    return True

def read_self_test_log(fd):
    cdb = (ctypes.c_ubyte * LOG_SENSE_LEN)(
        0x4D, 0xE0,      # LOG SENSE, PC=0 (current), Page=0x10  
        0x10, 0x00,       # Page Code = 0x10
        0x00, 0x00,       # Reserved
        0x00, (LOG_SENSE_REPLY_LEN >> 8) & 0xFF, (LOG_SENSE_REPLY_LEN & 0xFF), 0x00
    )
    data_buf = (ctypes.c_ubyte * LOG_SENSE_REPLY_LEN)()
    sense_buf = (ctypes.c_ubyte * SENSE_BUFFER_LEN)()

    hdr = sg_io_hdr()
    hdr.interface_id = ord('S')
    hdr.dxfer_direction = SG_DXFER_FROM_DEV
    hdr.cmd_len = LOG_SENSE_LEN
    hdr.mx_sb_len = SENSE_BUFFER_LEN
    hdr.dxfer_len = LOG_SENSE_REPLY_LEN
    hdr.dxferp = ctypes.cast(data_buf, ctypes.c_void_p)
    hdr.cmdp = ctypes.cast(cdb, ctypes.c_void_p)
    hdr.sbp = ctypes.cast(sense_buf, ctypes.c_void_p)
    hdr.timeout = 10000  # ms

    fcntl.ioctl(fd, SG_IO, hdr)

    # if hdr.status != 0:
    #     print("LOG SENSE command failed.")
    #     return None

    return bytes(data_buf)

def parse_self_test_results(data):
    if not data or len(data) < 4:
        print("No data to parse")
        return

    print("Parsing self-test results:")
    param_len = data[3] + 4
    i = 4
    while i + 4 < param_len:
        param_code = (data[i] << 8) | data[i+1]
        length = data[i+3]
        if param_code == 0x0001:  # Self-test results parameter
            entry = data[i+4:i+4+length]
            if not entry:
                print("No self-test result entry.")
            else:
                desc = entry[0] & 0x0F
                status = {
                    0: "Completed without error",
                    1: "Aborted by user",
                    2: "Aborted by device",
                    3: "Fatal error",
                    4: "Unknown error",
                    5: "Test in progress",
                    6: "Test failed",
                    7: "Partial failure"
                }.get(desc, f"Unknown status ({desc})")
                print(f"Self-test status: {status}")
                return
        i += 4 + length
    print("No self-test results found in log.")

def run_self_test(device="/dev/sda"):
    try:
        fd = os.open(device, os.O_RDONLY)
    except PermissionError:
        print("Permission denied. Use sudo.")
        return
    except Exception as e:
        print(f"Error opening device: {e}")
        return

    # print(f"Starting short self-test on {device}...")
    # if not send_self_test(fd):
    #     os.close(fd)
    #     return

    # print("Waiting for test to complete (5s)...")
    # time.sleep(5)

    print("Retrieving test result...")
    data = read_self_test_log(fd)
    os.close(fd)
    print(data)
    parse_self_test_results(data)

if __name__ == "__main__":
    dev = sys.argv[1] if len(sys.argv) > 1 else "/dev/sda"
    run_self_test(dev)
