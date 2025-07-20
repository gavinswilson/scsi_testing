import subprocess
import struct
import re


class scsi_device:
    def __init__(self, device: str):
        self.device = device
        self.size = 0
        self.block_size = 0
        self.no_blocks = 0
        self.serial_number = None
        self.model = None
        self.vendor = None  
        self.firmware_version = None
        
    def __repr__(self) -> str:
        """
        __repr__ is meant to provide an unambiguous string representation of the object.
        It's often used for debugging and should ideally return a string that could be used
        to recreate the object.
        """
        return f"scsi_device(device={self.device}, size={self.size}, block_size={self.block_size}, serial_number={self.serial_number}, model={self.model}, vendor={self.vendor}, firmware_version={self.firmware_version})"

    def __str__(self) -> str:
        """
        __str__ is meant to provide a readable string representation of the object.
        It's what gets shown when you print the object or convert it to a string.
        """
        return f"{self.device}, {self.size} bytes, {self.block_size} bytes/block, {self.serial_number}, {self.model}, {self.vendor}, {self.firmware_version}"


    def __parse_hex_from_stderr(self, stderr_text: str) -> bytes:
        """
        Extracts and returns the raw binary data from sg_raw's stderr hex dump
        Example line:
        Received 8 bytes of data:
        00     3b 9e 12 af 00 00 02 00
        """
        hex_bytes: list[int] = []
        for line in stderr_text.splitlines():
            # Match lines with hex bytes: e.g. "00     3b 9e 12 af 00 00 02 00"
            match = re.match(r'^\s*\d+\s+((?:[0-9a-fA-F]{2}\s+)+)', line)
            if match:
                hex_str = match.group(1)
                hex_bytes += [int(b, 16) for b in hex_str.strip().split()]
        
        return bytes(hex_bytes)


    def read_capacity(self) -> bool:
        # print(f"[+] Sending READ CAPACITY (10) to {self.device}")
        cmd: list[str] = ["sg_raw", "-r", "8", self.device, "25", "00", "00", "00", "00", "00", "00", "00", "00", "00"]

        data: str = ""  # Ensure 'data' is always defined
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

        rdata = self.__parse_hex_from_stderr(data)

        if len(rdata) < 8:
            raise RuntimeError("Failed to parse 8 bytes from stderr output")

        last_lba, block_len = struct.unpack(">II", rdata[:8])
        total_blocks = last_lba + 1
        self.size = total_blocks * block_len
        self.block_size = block_len
        self.no_blocks = total_blocks
        # print(f"\nParsed READ CAPACITY response:")
        # print(f"    Total blocks : {total_blocks}")
        # print(f"    Block size   : {block_len} bytes")

        return True

    def __sg_raw_read10(self, device: str, lba: int, num_blocks: int, block_size: int) -> bytes:
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

    def blank_check(self, device: str, total_blocks: int, block_size: int) -> bool:
        print(f"[+] Beginning blank check using READ(10)...")
        CHUNK_BLOCKS = 1000  # Number of blocks to read at a time
        lba = 0
        while lba < total_blocks:
            blocks_to_read = min(CHUNK_BLOCKS, total_blocks - lba)
            try:
                data = self.__sg_raw_read10(device, lba, blocks_to_read, block_size)
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