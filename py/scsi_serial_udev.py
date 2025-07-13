import pyudev
import sys

def get_serial_pyudev(device="/dev/sda"):
    context = pyudev.Context()
    try:
        dev = pyudev.Devices.from_device_file(context, device)
        serial = dev.get("ID_SERIAL_SHORT") or dev.get("ID_SERIAL") or "N/A"
        print(f"Serial Number ({device}): {serial}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    dev_path = sys.argv[1] if len(sys.argv) > 1 else "/dev/sda"
    get_serial_pyudev(dev_path)
