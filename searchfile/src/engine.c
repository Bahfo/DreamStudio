#include "file_list.h"

char* version_info = "COPYRIGHT 2026 EX-TECHNOLOGIES / DREAMSTUDIO\n"
                     "WATCHBIRD FILE TRACKER ENGINE __ VERSION 0.1\n"
                     "THIS IS AN INDEPENDENT VERSION OF WATCHBIRD \n"
                     "   FOR MORE INFO _ READ THE DOCUMENTATION   \n";

const char* engine_version(void)
{
    return version_info;
}

const char* py_watch_bird
(const char* directory, const char* query, int mode)
{
    return search_files(directory, query, mode);
}