
TARGET := scsi_serial
SOURCES := scsi_serial.c
OBJECTS := $(SOURCES:%.c=%.o)
CC := gcc
CFLAGS := 


all : $(TARGET)
	rm -f $(OBJECTS)
	@echo "Build complete."

debug: CFLAGS += -g
debug: $(TARGET)
	@echo "Debug build complete."

$(TARGET): $(OBJECTS) 
	$(CC) -o $@ $(OBJECTS) $(CFLAGS)

clean:
	rm -f $(TARGET) $(OBJECTS)*.o
	@echo "Cleaned up build files."

.PHONY: all clean
