import ctypes

def get_SN(device: str) -> str:
    """
    Calls the runCommand function from the shared library.
    """
    # Load the shared library
    my_lib = ctypes.CDLL('./talorem.so') # Adjust path and extension as needed

    # Define argument and return types for functions
    

    # Call the functions
    # input_str = "lsblk -J -e 7"
    # input_bytes = input_str.encode('utf-8')
    input_bytes = device.encode('utf-8')
    # Call the C++ function
    try:
        if "nvme" in device:
            my_lib.getSN_NVME.argtypes = [ctypes.c_char_p]
            my_lib.getSN_NVME.restype = ctypes.c_char_p
            output_bytes = my_lib.getSN_NVME(input_bytes)
        else:
            my_lib.getSN_SD.argtypes = [ctypes.c_char_p]
            my_lib.getSN_SD.restype = ctypes.c_char_p
            output_bytes = my_lib.getSN_SD(input_bytes)

        # Convert the returned bytes to a Python string
        output_str = output_bytes.decode('utf-8')
        return output_str
    except Exception as e:
        raise ValueError(f"Error calling runCommand: {e}")

def run_command(command: str) -> str:
    """
    Calls the runCommand function from the shared library.
    """
    # Load the shared library
    my_lib = ctypes.CDLL('./talorem.so') # Adjust path and extension as needed

    # Define argument and return types for functions
    my_lib.runCommand.argtypes = [ctypes.c_char_p]
    my_lib.runCommand.restype = ctypes.c_char_p

    # Call the functions
    # input_str = "lsblk -J -e 7"
    # input_bytes = input_str.encode('utf-8')
    input_bytes = command.encode('utf-8')
    # Call the C++ function
    try:
        output_bytes = my_lib.runCommand(input_bytes)

        # Convert the returned bytes to a Python string
        output_str = output_bytes.decode('utf-8')
        return output_str
    except Exception as e:
        raise ValueError(f"Error calling runCommand: {e}")
    
def get_drive_list():
    """
    Calls the runCommand function from the shared library to get the drive list.
    """
    command = "lsblk -J -e 7"
    output = run_command(command)
    if not output:
        return("No drivelist received")
    
    print(f"Drive List Output:\n{output}")
    return True

def get_main_drive():
    """
    Calls the runCommand function from the shared library to get the drive list.
    """
    command = "findmnt -n -o SOURCE /"
    output = run_command(command)
    if not output:
        return("No drive received")
    
    print(f"Drive List Output:\n{output}")
    return True

def main():
    """
    The main entry point of the program.
    """
    print("Program started.")
    try:
        if get_drive_list():
            print("Function executed successfully.")
        if get_main_drive():
            print("Function executed successfully.")
        sn_command = "/dev/nvme0"  # Example device path
        print(get_SN(sn_command))
    except ValueError as e:
        print(f"An error occurred: {e}")
    print("Program finished.")

if __name__ == "__main__":
    main()