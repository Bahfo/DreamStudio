CC = gcc
CFLAGS = -Wall -Wextra -O2 -fPIC -I.
LDFLAGS = -shared

SRC = file_list.c
OBJ = file_list.o
TARGET = search_engine.dll

all: $(TARGET)

$(OBJ): $(SRC)
	$(CC) $(CFLAGS) -c $< -o $@

$(TARGET): $(OBJ)
	$(CC) $(LDFLAGS) $(OBJ) -o $(TARGET)

clean:
	del /Q *.o *.dll

.PHONY: all clean
