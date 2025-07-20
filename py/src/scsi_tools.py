
import os

def scan_scsi_devices() -> list[str]:
    """
    Scans the system for all SCSI generic devices and returns a list of device paths.
    Example: ['/dev/sg0', '/dev/sg1']
    """
    sg_base_path = "/sys/class/scsi_generic"
    device_paths: list[str] = []

    if not os.path.isdir(sg_base_path):
        raise RuntimeError("SCSI generic interface not found (expected /sys/class/scsi_generic)")

    for entry in os.listdir(sg_base_path):
        dev_path = os.path.join("/dev", entry)
        if os.path.exists(dev_path):
            device_paths.append(dev_path)

    return sorted(device_paths)
