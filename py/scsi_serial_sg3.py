import subprocess
import sys
import re

def get_serial_sgutils(device="/dev/sda"):
    try:
        output = subprocess.check_output(["sg_inq", "-p", "0x80", device], stderr=subprocess.DEVNULL).decode()
        match = re.search(r"Unit serial number:\s*(.+)", output)
        if match:
            print(f"Serial Number ({device}): {match.group(1).strip()}")
        else:
            print(f"No serial found for {device}")
    except FileNotFoundError:
        print("Error: sg_inq not found. Please install sg3-utils.")
    except subprocess.CalledProcessError:
        print(f"Failed to query {device} (possibly unsupported or permission denied)")

if __name__ == "__main__":
    dev = sys.argv[1] if len(sys.argv) > 1 else "/dev/sda"
    get_serial_sgutils(dev)
