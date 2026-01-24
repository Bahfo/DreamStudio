#ifndef ENGINE_H
#define ENGINE_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stddef.h>

#define SEARCH_NAME 1
#define SEARCH_EXTN  2
#define SEARCH_PATH 3

#define BUFFERSIZE 65536

// List directory contents
__declspec(dllexport)
const char* list_directory(const char* path);

// Search files by name, extension, or path
__declspec(dllexport)
const char* search_files(const char* directory,
                         const char* query,
                         int mode);

#ifdef __cplusplus
}
#endif

#endif
