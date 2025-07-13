#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <scsi/sg.h>
#include <sys/ioctl.h>
#include <errno.h>

#define INQ_CMD_CODE 0x12
#define INQ_CMD_LEN 6
#define VPD_PAGE 0x80
#define SG_IO_HDR_LEN sizeof(sg_io_hdr_t)
#define INQ_REPLY_LEN 96
#define SENSE_BUFFER_LEN 32

int main(int argc, char *argv[]) {
    const char *device = "/dev/sda"; // Change this to your target device
    if (argc > 1) {
        device = argv[1];
    }

    int fd = open(device, O_RDONLY);
    if (fd < 0) {
        perror("Failed to open device");
        return 1;
    }

    unsigned char inquiry_cmd_blk[INQ_CMD_LEN] = {
        INQ_CMD_CODE, 0x01, VPD_PAGE, 0, INQ_REPLY_LEN, 0
    };

    unsigned char inquiry_buf[INQ_REPLY_LEN];
    unsigned char sense_buf[SENSE_BUFFER_LEN];

    memset(inquiry_buf, 0, sizeof(inquiry_buf));
    memset(sense_buf, 0, sizeof(sense_buf));

    sg_io_hdr_t io_hdr;
    memset(&io_hdr, 0, SG_IO_HDR_LEN);

    io_hdr.interface_id = 'S';
    io_hdr.dxfer_direction = SG_DXFER_FROM_DEV;
    io_hdr.cmd_len = sizeof(inquiry_cmd_blk);
    io_hdr.mx_sb_len = sizeof(sense_buf);
    io_hdr.dxfer_len = sizeof(inquiry_buf);
    io_hdr.dxferp = inquiry_buf;
    io_hdr.cmdp = inquiry_cmd_blk;
    io_hdr.sbp = sense_buf;
    io_hdr.timeout = 5000; // milliseconds

    if (ioctl(fd, SG_IO, &io_hdr) < 0) {
        perror("SG_IO ioctl failed");
        close(fd);
        return 1;
    }

    if ((io_hdr.info & SG_INFO_OK_MASK) != SG_INFO_OK) {
        fprintf(stderr, "SCSI command failed\n");
        close(fd);
        return 1;
    }

    int serial_len = inquiry_buf[3];
    if (serial_len <= 0 || serial_len > INQ_REPLY_LEN - 4) {
        fprintf(stderr, "Invalid serial length: %d\n", serial_len);
        close(fd);
        return 1;
    }

    printf("Serial Number: ");
    fwrite(&inquiry_buf[4], 1, serial_len, stdout);
    printf("\n");

    close(fd);
    return 0;
}
