#include <iostream>
#include <cstdio>
#include <memory>
#include <stdexcept>
#include <string>
#include <array>
#include <iostream>
#include <cstring>
#include <cstdlib>

extern "C" {
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
