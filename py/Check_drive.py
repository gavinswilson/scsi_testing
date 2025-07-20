import subprocess
import struct
import sys
import re

DEVICE = "/dev/sda"  # Change to your actual sg device
BLOCK_SIZE = 512     # We will get actual size from the device
CHUNK_BLOCKS = 128   # How many blocks to read per READ(10), tune for speed


def parse_hex_from_stderr(stderr_text):
    """
    Extracts and returns the raw binary data from sg_raw's stderr hex dump
    Example line:
    Received 8 bytes of data:
      00     3b 9e 12 af 00 00 02 00
    """
    hex_bytes = []
    for line in stderr_text.splitlines():
        # Match lines with hex bytes: e.g. "00     3b 9e 12 af 00 00 02 00"
        match = re.match(r'^\s*\d+\s+((?:[0-9a-fA-F]{2}\s+)+)', line)
        if match:
            hex_str = match.group(1)
            hex_bytes += [int(b, 16) for b in hex_str.strip().split()]
    
    return bytes(hex_bytes)


def run_sg_raw_read_capacity(device):
    print(f"[+] Sending READ CAPACITY (10) to {device}")
    cmd = ["sg_raw", "-r", "8",device, "25", "00", "00", "00", "00", "00", "00", "00", "00", "00"]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True  # <--- MUST be False to get raw bytes
            )
        data = result.stderr

        if len(data) < 8:
            raise RuntimeError("Invalid READ CAPACITY response")

    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")
        print(e.stderr.decode())

    ldata = parse_hex_from_stderr(data)

    if len(ldata) < 8:
        raise RuntimeError("Failed to parse 8 bytes from stderr output")

    last_lba, block_len = struct.unpack(">II", ldata[:8])
    total_blocks = last_lba + 1
    print(f"\nParsed READ CAPACITY response:")
    print(f"    Total blocks : {total_blocks}")
    print(f"    Block size   : {block_len} bytes")

    return total_blocks, block_len

def sg_raw_read10(device, lba, num_blocks, block_size):
    lba_bytes = struct.pack(">I", lba)
    blocks_byte = struct.pack(">H", num_blocks)

    # Construct READ(10) CDB: 28 00 [LBA:4] 00 [TransferLen:2] 00
    cdb = [
        "28", "00",
        f"{lba_bytes[0]:02x}", f"{lba_bytes[1]:02x}", f"{lba_bytes[2]:02x}", f"{lba_bytes[3]:02x}",
        "00",
        f"{blocks_byte[0]:02x}", f"{blocks_byte[1]:02x}",
        "00"
    ]

    read_len = num_blocks * block_size
    cmd = ["sg_raw", "-r", str(read_len), device] + cdb
    result = subprocess.run(cmd, capture_output=True, check=True)
    return result.stdout

def blank_check(device, total_blocks, block_size):
    print(f"[+] Beginning blank check using READ(10)...")
    lba = 0
    while lba < total_blocks:
        blocks_to_read = min(CHUNK_BLOCKS, total_blocks - lba)
        try:
            data = sg_raw_read10(device, lba, blocks_to_read, block_size)
            if any(byte != 0x00 for byte in data):
                print(f"[!] Non-zero data found at LBA {lba}")
                return False
        except subprocess.CalledProcessError as e:
            print(f"[!] READ(10) failed at LBA {lba}: {e}")
            return False

        print(f"    Checked up to block {lba + blocks_to_read} / {total_blocks}", end="\r")
        lba += blocks_to_read

    print("\n[+] Blank check successful. All data is zero.")
    return True

if __name__ == "__main__":
    dev = sys.argv[1] if len(sys.argv) > 1 else "/dev/sda"
    total_blocks, block_size = run_sg_raw_read_capacity(DEVICE)
    # blank_check(DEVICE, total_blocks, block_size)