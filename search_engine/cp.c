#include "searchFile.h"
#include <stdio.h>
#include <fcntl.h>

//COPY FILES FROM SOURCE TO DESTINATION: 
//SYNTAX: copy.exe src dest    ---> copy from source to destination
//        copy.exe src1 src2 ... dest ---> copy all source files to
//        the destination directory

#define MEM_SIZE 64

int copy(int argc, char *argv[])
{
    //argc: argument counter: must be one integer value bigger
    //than the number of arguments.
    //Example: If arguments = 2 => cp file1 file2 (cp is main arg)

    //argv: argument values, a pointer to an array of arguments
    printf("Copying file ...\n");

    //Possible Error Messages
    if (argc == 1)
    {
        printf("ERROR: missing file operand after %s\n", argv[0]);
        printf("Check documentation for more info\n");
        return 0;
    }
    else if (argc == 2)
    {
        printf("%s: missing destination file after %s\n", argv[0], argv[1]);
        printf("Check documentation for more info");
        return 0;
    }
    char MEM_BUFFER[MEM_SIZE];
    int  number_of_bytes;

    //O_RDONLY: Read-Only Flag for only reading contents without
    //          modifications
    int source_file = open(argv[2], 0, O_RDONLY);
    printf("fd = %d\n", source_file);

    number_of_bytes = read(source_file, MEM_BUFFER, MEM_SIZE);

    int target_file = open(argv[3], O_CREAT, O_WRONLY);
    write(target_file, MEM_BUFFER, number_of_bytes);
}