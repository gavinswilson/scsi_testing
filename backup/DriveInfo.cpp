#include <iostream>
#include <filesystem>
#include <fstream>
#include <string>
#include <cstdio>
#include <array>
#include <sstream>
#include <vector>
#include <iomanip>

void list_disks_lsblk() {
    // lsblk: list only disks (-d), show desired columns, no header
    std::cout << "lsblk:" << std::endl;
    const char* cmd = "lsblk -e 7 -d -o NAME,VENDOR,MODEL,SERIAL,TRAN,SIZE --noheadings";
    FILE *pipe = popen(cmd, "r");
    if (!pipe) {
        std::cerr << "Failed to run lsblk command.\n";
        return;
    }

    char buffer[512];
    while (fgets(buffer, sizeof(buffer), pipe)) {
        std::string line(buffer);

        // Remove trailing newline
        if (!line.empty() && line.back() == '\n')
            line.pop_back();

        std::istringstream iss(line);
        std::string name, vendor, model, serial, tran, size;

        // Read device name and vendor first
        if (!(iss >> name >> vendor)) continue;

        // Model may contain spaces; read until we get to serial
        model.clear();
        std::string token;
        while (iss >> token) {
            if (iss.peek() == EOF) break; // last token
            model += (model.empty() ? "" : " ") + token;
        }

        // Serial, tran, size are usually last three tokens
        if (!(iss >> serial >> tran >> size)) {
            serial = "?";
            tran = "?";
            size = "?";
        }

        // Print disk info directly
        std::cout << "/dev/" << name
                  << "  Vendor: " << vendor
                  << "  Model: " << model
                  << "  Serial: " << serial
                  << "  Transport: " << tran
                  << "  Size: " << size
                  << std::endl;
    }

    pclose(pipe);
}


namespace fs = std::filesystem;

std::string read_first_line(const std::string &path) {
    std::ifstream f(path);
    std::string line;
    if (f && std::getline(f, line))
        return line;
    return {};
}

void list_disks_with_serial() {
    std::cout << "Scsi:" << std::endl;
    std::string sys_block = "/sys/block";

    for (const auto &entry : fs::directory_iterator(sys_block)) {
        std::string dev = entry.path().filename().string();
        std::string base = entry.path().string();

        // skip non-physical devices
        if (dev.find("loop") == 0 || dev.find("ram") == 0 || dev.find("dm-") == 0)
            continue;

        std::string rotational = read_first_line(base + "/queue/rotational");
        std::string model = read_first_line(base + "/device/model");
        std::string vendor = read_first_line(base + "/device/vendor");
        std::string size = read_first_line(base + "/size");
        std::string serial = read_first_line(base + "/device/serial");

        // NVMe serial fallback
        if (serial.empty() && dev.rfind("nvme", 0) == 0) {
            serial = read_first_line(base + "/device/device/serial");
        }

        std::cout << "/dev/" << dev
                  << "  Vendor: " << (vendor.empty() ? "?" : vendor)
                  << "  Model: " << (model.empty() ? "?" : model)
                  << "  Serial: " << (serial.empty() ? "?" : serial);

        if (!rotational.empty())
            std::cout << "  Type: " << (rotational == "0" ? "SSD" : "HDD");

        if (!size.empty()) {
            try {
                uint64_t sectors = std::stoull(size);
                double gb = sectors * 512.0 / 1e9;
                std::cout << "  Size: " << gb << " GB";
            } catch (...) {}
        }

        std::cout << std::endl;
    }
}

std::string run_command(const std::string &cmd) {
    std::array<char, 512> buffer{};
    std::string result;
    FILE *pipe = popen(cmd.c_str(), "r");
    if (!pipe) return "";
    while (fgets(buffer.data(), buffer.size(), pipe)) {
        result += buffer.data();
    }
    pclose(pipe);
    return result;
}

void list_drives_hdparm() {
    std::cout << "hdparm:" << std::endl;
    
    for (const auto &entry : fs::directory_iterator("/dev")) {
        std::string dev = entry.path().filename().string();
        if (dev.rfind("sd", 0) == 0 && dev.size() == 3) {  // /dev/sda, /dev/sdb, etc.
            std::string path = "/dev/" + dev;
            std::string cmd = "sudo hdparm -I " + path + " 2>/dev/null";
            std::string output = run_command(cmd);

            if (output.empty()) continue;

            // Extract serial and model
            std::string serial, model;
            size_t pos_model = output.find("Model Number:");
            if (pos_model != std::string::npos)
                model = output.substr(pos_model + 13, output.find('\n', pos_model) - pos_model - 13);

            size_t pos_serial = output.find("Serial Number:");
            if (pos_serial != std::string::npos)
                serial = output.substr(pos_serial + 15, output.find('\n', pos_serial) - pos_serial - 15);

            std::cout << path
                      << "  Model:" << (model.empty() ? "?" : model)
                      << "  Serial:" << (serial.empty() ? "?" : serial)
                      << std::endl;
        }
    }
}

void list_nvme_drives() {
    std::cout << "nvme:" << std::endl;
    
    for (const auto &entry : fs::directory_iterator("/dev")) {
        std::string dev = entry.path().filename().string();
        if (dev.rfind("nvme", 0) == 0 && dev.find('n') != std::string::npos && dev.find('p') == std::string::npos) {
            // match /dev/nvme0n1, /dev/nvme1n1, etc. but not partitions
            std::string path = "/dev/" + dev;
            std::string cmd = "sudo nvme id-ctrl " + path + " 2>/dev/null";
            std::string output = run_command(cmd);

            if (output.empty()) continue;

            std::string serial, model;
            size_t pos_sn = output.find("sn");
            if (pos_sn != std::string::npos)
                serial = output.substr(pos_sn + 5, output.find('\n', pos_sn) - pos_sn - 5);

            size_t pos_mn = output.find("mn");
            if (pos_mn != std::string::npos)
                model = output.substr(pos_mn + 5, output.find('\n', pos_mn) - pos_mn - 5);

            std::cout << path
                      << "  Model:" << (model.empty() ? "?" : model)
                      << "  Serial:" << (serial.empty() ? "?" : serial)
                      << std::endl;
        }
    }
}


void list_disks_parted() {
    std::cout << "parted:" << std::endl;
    
    FILE* pipe = popen("sudo parted -l 2>/dev/null", "r");
    if (!pipe) {
        std::cerr << "Failed to run parted.\n";
        return;
    }

    char buffer[512];
    std::string model, disk, size;
    while (fgets(buffer, sizeof(buffer), pipe)) {
        std::string line(buffer);

        // Parse Model line
        if (line.find("Model:") != std::string::npos) {
            size_t pos = line.find("Model:");
            model = line.substr(pos + 6);
            // remove trailing whitespace/newline
            model.erase(model.find_last_not_of(" \n\r\t") + 1);
        }

        // Parse Disk line
        if (line.find("Disk /dev/") != std::string::npos) {
            std::istringstream iss(line);
            std::string token;
            iss >> token; // Disk
            iss >> disk;  // /dev/sda:
            if (!disk.empty() && disk.back() == ':') disk.pop_back();
            iss >> size;  // size value
            std::string size_unit;
            iss >> size_unit;
            if (!size_unit.empty()) size += size_unit;

            std::cout << disk
                      << "  Model: " << model
                      << "  Size: " << size
                      << std::endl;
        }
    }

    pclose(pipe);
}

void list_disks_lshw() {
    std::cout << "lshw:" << std::endl;
    FILE* pipe = popen("sudo lshw -class disk 2>/dev/null", "r");
    if (!pipe) {
        std::cerr << "Failed to run lshw.\n";
        return;
    }

    char buffer[512];
    std::string disk, product, serial, size;
    while (fgets(buffer, sizeof(buffer), pipe)) {
        std::string line(buffer);

        if (line.find("logical name:") != std::string::npos) {
            disk = line.substr(line.find(":") + 1);
            disk.erase(0, disk.find_first_not_of(" \t"));
            disk.erase(disk.find_last_not_of(" \n\r\t") + 1);
        } else if (line.find("product:") != std::string::npos) {
            product = line.substr(line.find(":") + 1);
            product.erase(0, product.find_first_not_of(" \t"));
            product.erase(product.find_last_not_of(" \n\r\t") + 1);
        } else if (line.find("serial:") != std::string::npos) {
            serial = line.substr(line.find(":") + 1);
            serial.erase(0, serial.find_first_not_of(" \t"));
            serial.erase(serial.find_last_not_of(" \n\r\t") + 1);
        } else if (line.find("size:") != std::string::npos) {
            size = line.substr(line.find(":") + 1);
            size.erase(0, size.find_first_not_of(" \t"));
            size.erase(size.find_last_not_of(" \n\r\t") + 1);
        }

        // print when we have a disk name
        if (!disk.empty() && !product.empty() && !size.empty()) {
            std::cout << disk
                      << "  Model: " << product
                      << "  Serial: " << (serial.empty() ? "?" : serial)
                      << "  Size: " << size
                      << std::endl;
            // clear for next disk
            disk.clear();
            product.clear();
            serial.clear();
            size.clear();
        }
    }

    pclose(pipe);
}

int main() {
    list_disks_with_serial();
    list_drives_hdparm();
    list_nvme_drives();
    list_disks_lsblk();
    list_disks_parted();
    list_disks_lshw();
    return 0;
}

