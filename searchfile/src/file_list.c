#include <windows.h>
#include <stdbool.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#include "file_list.h"

#define BUFFERSIZE 65536

__declspec(dllexport)
const char* list_directory(const char* FILE_PATH)
{
    static char BUFFER[BUFFERSIZE];
    BUFFER[0] = '\0';

    char SEARCHPATH[MAX_PATH];
    snprintf(SEARCHPATH, MAX_PATH, "%s\\*", FILE_PATH);

    WIN32_FIND_DATAA FIND_DATA;
    HANDLE HANDLE_FIND = FindFirstFileA(SEARCHPATH, &FIND_DATA);

    if (HANDLE_FIND == INVALID_HANDLE_VALUE)
    {
        snprintf(BUFFER, BUFFERSIZE, "ERROR: Cannot open directory\n");
        return BUFFER;
    }

    do
    {
        const char* TYPE = (FIND_DATA.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)
                           ? "DIR" : "FILE";

        size_t len = strlen(BUFFER);
        if (len >= BUFFERSIZE - 256)
            break;

        snprintf(
            BUFFER + len,
            BUFFERSIZE - len,
            "%s|%s|%lu|%lu\n",
            TYPE,
            FIND_DATA.cFileName,
            FIND_DATA.nFileSizeLow,
            FIND_DATA.ftLastWriteTime.dwLowDateTime
        );

    } while (FindNextFileA(HANDLE_FIND, &FIND_DATA));

    FindClose(HANDLE_FIND);
    return BUFFER;
}

static int match(
    const char* FILENAME,
    const char* FULLPATH,
    const char* QUERY,
    int mode
)
{
    switch (mode)
    {
        case SEARCH_NAME:
            return strstr(FILENAME, QUERY) != NULL;

        case SEARCH_EXTN: {
            const char* dot = strrchr(FILENAME, '.');
            return dot && strcmp(dot, QUERY) == 0;
        }

        case SEARCH_PATH:
            return strstr(FULLPATH, QUERY) != NULL;

        default:
            return 0;
    }
}

__declspec(dllexport)
const char* search_files(
    const char* DIRECTORY_NAME,
    const char* QUERY,
    int MODE
)
{
    static char BUFFER[BUFFERSIZE];
    BUFFER[0] = '\0';

    char search_path[MAX_PATH];
    snprintf(search_path, MAX_PATH, "%s\\*", DIRECTORY_NAME);

    WIN32_FIND_DATAA DATA;
    HANDLE HANDLE_FIND = FindFirstFileA(search_path, &DATA);

    if (HANDLE_FIND == INVALID_HANDLE_VALUE)
    {
        snprintf(BUFFER, BUFFERSIZE, "ERROR: Cannot open directory\n");
        return BUFFER;
    }

    do
    {
        if (DATA.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)
            continue;

        char FULLPATH[MAX_PATH];
        _snprintf_s(FULLPATH, MAX_PATH, _TRUNCATE, "%s\\%s", DIRECTORY_NAME, DATA.cFileName);

        if (match(DATA.cFileName, FULLPATH, QUERY, MODE))
        {
            size_t len = strlen(BUFFER);
            if (len >= BUFFERSIZE - 256)
                break;

            snprintf(
                BUFFER + len,
                BUFFERSIZE - len,
                "FILE|%s|%lu\n",
                FULLPATH,
                DATA.nFileSizeLow
            );
        }

    } while (FindNextFileA(HANDLE_FIND, &DATA));

    FindClose(HANDLE_FIND);
    return BUFFER;
}
