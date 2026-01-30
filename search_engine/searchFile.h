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

typedef struct
{
    char **file_name;
    char **file_extn;
    size_t count;
} FilesType;

typedef struct
{
    char **name;
    char **extn;
    char **path;
    char **lang;
    float prcnt;
    size_t count;
    size_t capacity;
} DirectorySummary;

//General method in Windows to list and store the 
//contents of a directory given, in a struct, on Windows.
FilesList lscwd(const char *FilePath);

//Comprehinsed method to analyze a directory, giving a
//summary of listed files, languages (by extensions) and
//detailed overview of directory
// void scancwd(const char *FilePath);

//Method to analyze a file, counting number of lines, the
//file type, etc. 
// void scanfile(const char *FilePath, const char *FileName);

#endif