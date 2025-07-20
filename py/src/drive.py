from scsi_class import scsi_device
from scsi_tools import scan_scsi_devices

import sys

def main():
    if len(sys.argv) != 2:
        print("Usage: python run_drive_size_check.py /dev/sgX")
        sys.exit(1)
    devices = scan_scsi_devices()
    print(f"Found SCSI devices: {devices}")
    device_path = sys.argv[1]
    
    if device_path not in devices:
        print(f"[!] Device {device_path} not found.")
        sys.exit(1)
    
    dev = scsi_device(device_path)

    try:
        total_blocks, block_size = dev.run_sg_raw_read_capacity(device_path)
        dev.size = total_blocks * block_size
        dev.block_size = block_size

        print("\n[+] Device Summary:")
        print(dev)

    except Exception as e:
        print(f"[!] Failed to query drive size: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
