#include <stdio.h>
#include <ctype.h>
#include <stdlib.h>


void view_file(FILE* file) {
    unsigned char buffer[1024];
    size_t bytes_read;
    long offset = 0;

    while (bytes_read = fread(buffer, 1, bytes_read, file)) {
        
    }
    
}

int main() {
    return 0;
}