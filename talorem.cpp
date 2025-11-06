#include <iostream>
#include <cstdio>
#include <memory>
#include <stdexcept>
#include <string>
#include <array>
#include <iostream>
#include <cstring>
#include <cstdlib>
#include <vector>
#include <fcntl.h>
#include <unistd.h>
#include <scsi/sg.h>
#include <sys/ioctl.h>
#include <errno.h>
#include <unistd.h>
#include <linux/nvme_ioctl.h>
#include <cstring>

struct nvme_id_ctrl {
    uint16_t vid;
    uint16_t ssvid;
    char sn[20];
    char mn[40];
    char fr[8];
    uint8_t rab;
    uint8_t ieee[3];
    // (fields omitted for brevity)
};

constexpr uint8_t INQ_CMD_CODE = 0x12;
constexpr uint8_t INQ_CMD_LEN = 6;
constexpr uint8_t VPD_PAGE = 0x80;
constexpr size_t INQ_REPLY_LEN = 96;
constexpr size_t SENSE_BUFFER_LEN = 32;

extern "C" {

    const char*  getSN_NVME(const char* cmd) {
        const char* device = "/dev/nvme0n1";
        // const char* device = cmd;
        std::cout << "Getting SN for device: " << device << std::endl;
        int fd = open(device, O_RDONLY);
        if (fd < 0) {
            perror("Failed to open NVMe device");
            return "1";
        }
        
        nvme_id_ctrl id_ctrl{};
        int ret = ioctl(fd, NVME_IOCTL_ID, &id_ctrl);
        if (ret < 0) {
            perror("NVMe ioctl failed");
            close(fd);
            return "1";
        }

        // Print serial number
        std::string sn(id_ctrl.sn, sizeof(id_ctrl.sn));
        sn.erase(sn.find_last_not_of(' ') + 1);

        std::cout << "Serial Number: " << sn << std::endl;

        close(fd);
        return "0";
    }


    const char*  getSN_SD(const char* cmd) {
        // const char* device = "/dev/sda"; // Default device path
        const char* device = cmd;
        std::cout << "Getting SN for device: " << device << std::endl;
        int fd = open(device, O_RDONLY);
        if (fd < 0) {
            std::perror("Failed to open device");
            return "1";
        }

        unsigned char inquiry_cmd_blk[INQ_CMD_LEN] = {
            INQ_CMD_CODE, 0x01, VPD_PAGE, 0, static_cast<unsigned char>(INQ_REPLY_LEN), 0
        };

        std::vector<unsigned char> inquiry_buf(INQ_REPLY_LEN, 0);
        std::vector<unsigned char> sense_buf(SENSE_BUFFER_LEN, 0);

        sg_io_hdr_t io_hdr;
        std::memset(&io_hdr, 0, sizeof(io_hdr));

        io_hdr.interface_id = 'S';
        io_hdr.dxfer_direction = SG_DXFER_FROM_DEV;
        io_hdr.cmd_len = sizeof(inquiry_cmd_blk);
        io_hdr.mx_sb_len = sense_buf.size();
        io_hdr.dxfer_len = inquiry_buf.size();
        io_hdr.dxferp = inquiry_buf.data();
        io_hdr.cmdp = inquiry_cmd_blk;
        io_hdr.sbp = sense_buf.data();
        io_hdr.timeout = 5000; // milliseconds

        if (ioctl(fd, SG_IO, &io_hdr) < 0) {
            std::perror("SG_IO ioctl failed");
            close(fd);
            return "1";
        }

        if ((io_hdr.info & SG_INFO_OK_MASK) != SG_INFO_OK) {
            std::cerr << "SCSI command failed" << std::endl;
            close(fd);
            return "1";
        }

        int serial_len = inquiry_buf[3];
        if (serial_len <= 0 || serial_len > static_cast<int>(INQ_REPLY_LEN - 4)) {
            std::cerr << "Invalid serial length: " << serial_len << std::endl;
            close(fd);
            return "1";
        }

        std::cout << "Serial Number: ";
        // SN = 
        std::cout.write(reinterpret_cast<const char*>(&inquiry_buf[4]), serial_len);
        std::cout << std::endl;

        close(fd);
        return "Serial Retrieved";
    }
    const char*  runCommand(const char* cmd) {
        std::string s_cmd(cmd);
        std::array<char, 128> buffer;
        std::string result;

        // Open pipe to the command
        FILE* pipe = popen(s_cmd.c_str(), "r");
        if (!pipe) {
            throw std::runtime_error("popen() failed!");
        }

        // Read all output
        while (fgets(buffer.data(), buffer.size(), pipe) != nullptr) {
            result += buffer.data();
        }

        // Close pipe and return
        int retCode = pclose(pipe);
        if (retCode != 0) {
            // optional: throw or handle non-zero exit code
        }
        char* output_result = (char*)malloc(result.length() + 1);
        if (output_result == NULL) return NULL;
        std::strcpy(output_result, result.c_str());
        return output_result;
    }
};
// Example usage
// int main() {
//     try {
//         std::string output = runCommand("lsblk -J -e 7");
//         std::cout << "Command output:\n" << output << std::endl;
//     } catch (const std::exception& ex) {
//         std::cerr << "Error: " << ex.what() << std::endl;
//     }
//     try {
//         std::string output = runCommand("findmnt -n -o SOURCE /");
//         std::cout << "Mounted on Disk:\n" << output << std::endl;
//     } catch (const std::exception& ex) {
//         std::cerr << "Error: " << ex.what() << std::endl;
//     }
// }
