#include <iostream>
#include <cstdio>
#include <string>
#include <sstream>
#include <algorithm>

// Utility trim function
std::string trim(const std::string& s) {
    size_t start = s.find_first_not_of(" \t\n\r");
    if (start == std::string::npos) return "";
    size_t end = s.find_last_not_of(" \t\n\r");
    return s.substr(start, end - start + 1);
}

// ---------------------- 1. SCSI (lsscsi) ----------------------
void list_disks_scsi() {
    FILE* pipe = popen("lsscsi", "r");
    if (!pipe) { std::cerr << "Failed to run lsscsi\n"; return; }

    char buffer[512];
    while (fgets(buffer, sizeof(buffer), pipe)) {
        std::string line = trim(buffer);
        if (line.empty()) continue;

        // Example lsscsi line: [0:0:0:0]    disk    ATA     Samsung SSD 860  1B6Q  /dev/sda
        std::istringstream iss(line);
        std::string id, type, vendor, model, revision, device;

        if (!(iss >> id >> type >> vendor)) continue;

        // Read model until revision
        std::string token;
        model.clear();
        while (iss >> token) {
            if (token.find("/") == 0) { // device name
                device = token;
                break;
            }
            model += (model.empty() ? "" : " ") + token;
        }

        std::cout << device
                  << "  Model: " << model
                  << "  Serial: ?"
                  << "  Size: ?"
                  << "  Transport: SCSI"
                  << std::endl;
    }
    pclose(pipe);
}

// ---------------------- 2. hdparm ----------------------
void list_disks_hdparm() {
    FILE* pipe = popen("ls /dev/sd?", "r");
    if (!pipe) { std::cerr << "Failed to list /dev/sd?\n"; return; }

    char buffer[128];
    while (fgets(buffer, sizeof(buffer), pipe)) {
        std::string dev = trim(buffer);
        if (dev.empty()) continue;

        // Get model and serial via hdparm
        std::string cmd = "sudo hdparm -I " + dev + " 2>/dev/null";
        FILE* hdpipe = popen(cmd.c_str(), "r");
        if (!hdpipe) continue;

        std::string model, serial;
        char line[512];
        while (fgets(line, sizeof(line), hdpipe)) {
            std::string sline = trim(line);
            if (sline.find("Model Number:") != std::string::npos)
                model = trim(sline.substr(13));
            else if (sline.find("Serial Number:") != std::string::npos)
                serial = trim(sline.substr(14));
        }
        pclose(hdpipe);

        std::cout << dev
                  << "  Model: " << (model.empty() ? "?" : model)
                  << "  Serial: " << (serial.empty() ? "?" : serial)
                  << "  Size: ?"
                  << "  Transport: SATA"
                  << std::endl;
    }
    pclose(pipe);
}

// ---------------------- 3. NVMe (nvme-cli) ----------------------
void list_disks_nvme() {
    FILE* pipe = popen("ls /dev/nvme[0-9] 2>/dev/null", "r");
    if (!pipe) return;

    char buffer[128];
    while (fgets(buffer, sizeof(buffer), pipe)) {
        std::string ctrl = trim(buffer);
        if (ctrl.empty()) continue;

        std::string cmd = "sudo nvme id-ctrl " + ctrl + " 2>/dev/null";
        FILE* nvpipe = popen(cmd.c_str(), "r");
        if (!nvpipe) continue;

        std::string model, serial;
        char line[512];
        while (fgets(line, sizeof(line), nvpipe)) {
            std::string sline = trim(line);
            if (sline.find("mn     :") == 0)
                model = trim(sline.substr(8));
            else if (sline.find("sn     :") == 0)
                serial = trim(sline.substr(8));
        }
        pclose(nvpipe);

        // Find the first namespace for reporting
        std::string dev = ctrl + "n1";
        std::cout << dev
                  << "  Model: " << (model.empty() ? "?" : model)
                  << "  Serial: " << (serial.empty() ? "?" : serial)
                  << "  Size: ?"
                  << "  Transport: NVMe"
                  << std::endl;
    }
    pclose(pipe);
}



// ---------------------- 4. lsblk ----------------------
void list_disks_lsblk() {
    FILE* pipe = popen("lsblk -e 7 -d -o NAME,SIZE,TRAN --noheadings", "r");
    if (!pipe) return;

    char buffer[512];
    while (fgets(buffer, sizeof(buffer), pipe)) {
        std::string line = trim(buffer);
        if (line.empty()) continue;

        std::istringstream iss(line);
        std::string name, size, tran;
        iss >> name >> size >> tran;
        if (name.empty()) continue;

        std::cout << "/dev/" << name
                  << "  Model: ?"
                  << "  Serial: ?"
                  << "  Size: " << (size.empty() ? "?" : size)
                  << "  Transport: " << (tran.empty() ? "?" : tran)
                  << std::endl;
    }
    pclose(pipe);
}

// ---------------------- 5. parted -l ----------------------
void list_disks_parted() {
    FILE* pipe = popen("sudo parted -l 2>/dev/null", "r");
    if (!pipe) return;

    std::string model, disk, size;
    char buffer[512];
    while (fgets(buffer, sizeof(buffer), pipe)) {
        std::string line = trim(buffer);
        if (line.find("Model:") == 0)
            model = trim(line.substr(6));
        else if (line.find("Disk /dev/") == 0) {
            std::istringstream iss(line);
            std::string token;
            iss >> token; // Disk
            iss >> disk;  // /dev/sda:
            if (!disk.empty() && disk.back() == ':') disk.pop_back();
            iss >> size;
            std::string unit;
            iss >> unit;
            if (!unit.empty()) size += unit;

            std::cout << disk
                      << "  Model: " << (model.empty() ? "?" : model)
                      << "  Serial: ?"
                      << "  Size: " << (size.empty() ? "?" : size)
                      << "  Transport: ?"
                      << std::endl;
        }
    }
    pclose(pipe);
}

// ---------------------- 6. lshw -class disk ----------------------
void list_disks_lshw() {
    FILE* pipe = popen("sudo lshw -class disk 2>/dev/null", "r");
    if (!pipe) return;

    std::string disk, product, serial, size;
    char lineBuffer[1024];
    bool inDiskBlock = false;

    while (fgets(lineBuffer, sizeof(lineBuffer), pipe)) {
        std::string line = trim(lineBuffer);
        if (line.empty()) continue;

        // Start of a disk block
        if (line.find("*-disk") != std::string::npos) {
            // Print previous block if it exists
            if (!disk.empty() || !product.empty() || !size.empty()) {
                std::cout << (disk.empty() ? "?" : disk)
                          << "  Model: " << (product.empty() ? "?" : product)
                          << "  Serial: " << (serial.empty() ? "?" : serial)
                          << "  Size: " << (size.empty() ? "?" : size)
                          << "  Transport: ?"
                          << std::endl;
            }
            // Reset for new block
            disk.clear(); product.clear(); serial.clear(); size.clear();
            inDiskBlock = true;
            continue;
        }

        if (!inDiskBlock) continue;

        if (line.find("logical name:") == 0)
            disk = trim(line.substr(13));
        else if (line.find("product:") == 0)
            product = trim(line.substr(8));
        else if (line.find("serial:") == 0)
            serial = trim(line.substr(7));
        else if (line.find("size:") == 0)
            size = trim(line.substr(5));
    }

    // Print last block if needed
    if (!disk.empty() || !product.empty() || !size.empty()) {
        std::cout << (disk.empty() ? "?" : disk)
                  << "  Model: " << (product.empty() ? "?" : product)
                  << "  Serial: " << (serial.empty() ? "?" : serial)
                  << "  Size: " << (size.empty() ? "?" : size)
                  << "  Transport: ?"
                  << std::endl;
    }

    pclose(pipe);
}


// ---------------------- main ----------------------
int main() {
    std::cout << "--- SCSI ---\n"; list_disks_scsi();
    std::cout << "\n--- hdparm ---\n"; list_disks_hdparm();
    std::cout << "\n--- NVMe ---\n"; list_disks_nvme();
    std::cout << "\n--- lsblk ---\n"; list_disks_lsblk();
    std::cout << "\n--- parted ---\n"; list_disks_parted();
    std::cout << "\n--- lshw ---\n"; list_disks_lshw();
    return 0;
}
