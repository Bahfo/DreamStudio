#ifdef _WIN32
// Windows API code
#include <windows.h>
#include <stdbool.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#define WIN32_LEAN_AND_MEAN

#define API __declsepc(dllexport)

typedef struct
{
    char **names;
    size_t count;
} FilesList;

//General Method in Windows to list and store the 
//contents of a directory given, in a struct, on Windows.
FilesList lscwd(const char *FilePath);

#endif