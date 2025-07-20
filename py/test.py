import subprocess

def send_scsi_command(device_path, command_bytes, request_len=0, output_file=None):
    """
    Sends a SCSI command to a device using sg_raw.

    Args:
        device_path (str): The path to the SCSI device (e.g., /dev/sg0, /dev/sdb).
        command_bytes (list): A list of integers representing the SCSI command bytes in hexadecimal format.
        request_len (int, optional): The expected length of the data-in phase (bytes). Defaults to 0 (no data-in).
        output_file (str, optional): Path to a file to write the received data to. Defaults to None (print to stdout).
    Returns:
        tuple: A tuple containing the stdout and stderr from the sg_raw command.
    """
    cmd = ["sg_raw", device_path]
    if request_len > 0:
        cmd.extend(["--request", str(request_len)])
    if output_file:
        cmd.extend(["--outfile", output_file])
    for byte in command_bytes:
        cmd.append(f"{byte:02x}")  # Convert to two-digit hex string

    try:
        result = subprocess.run(cmd, capture_output=True, text=False, check=True)
        stdout = result.stdout  # raw bytes
        stderr = result.stderr.decode()
        return stdout, stderr
    except subprocess.CalledProcessError as e:
        print(f"Error executing sg_raw: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return e.stdout, e.stderr

# Example: Perform an INQUIRY command to retrieve device information
device_path = "/dev/sda"  # Replace with your SCSI device path
inquiry_command = [0x12, 0x00, 0x00, 0x00, 0x24, 0x00]  # Standard INQUIRY command (6-byte CDB)
inquiry_response_len = 36  # Standard INQUIRY response length

stdout, stderr = send_scsi_command(device_path, inquiry_command, inquiry_response_len)

if stdout:
    print("INQUIRY Raw Data (hex):")
    print(stdout.hex())
    print("INQUIRY as bytes:")
    print(list(stdout))
if stderr:
    print("\nsg_raw stderr output:")
    print(stderr)

inquiry_command = [0x25, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]  # Standard INQUIRY command (6-byte CDB)
inquiry_response_len = 36  # Standard INQUIRY response length

stdout, stderr = send_scsi_command(device_path, inquiry_command, inquiry_response_len)

if stdout:
    print("INQUIRY Raw Data (hex):")
    print(stdout.hex())
    print("INQUIRY as bytes:")
    print(list(stdout))
if stderr:
    print("\nsg_raw stderr output:")
    print(stderr)

# Example: Read 512 bytes from a buffer (mode 2) and save to a file
# Note: You'll need to create a dummy file 'i512.bin' for this to work as expected.
# For testing purposes, you could create it with: dd if=/dev/urandom bs=512 count=1 of=i512.bin
# write_buffer_command = [0x3c, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x00, 0x00] # READ BUFFER command
# read_buffer_response_len = 512
# output_file = "o512.bin"

# # Assuming 'i512.bin' exists and contains data
# stdout, stderr = send_scsi_command(device_path, write_buffer_command, request_len=read_buffer_response_len, output_file=output_file)

# if stdout:
#     print("WRITE BUFFER Response (stdout):")
#     print(stdout)
# if stderr:
#     print("sg_raw Error/Warning (stderr):")
#     print(stderr)

