# Compiler and flags
CXX := g++
CXXFLAGS := -shared -fPIC -o

# Target executable
TARGET := talorem.so

# Source files (all .cpp files in current directory)
SRCS := $(wildcard *.cpp)

# Object files
OBJS := $(SRCS:.cpp=.so)

# Default rule
all: $(TARGET)

# Compile .cpp into .o
%.so: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

# Clean build files
clean:
	rm -f $(OBJS) $(TARGET)

# Phony targets
.PHONY: all clean
