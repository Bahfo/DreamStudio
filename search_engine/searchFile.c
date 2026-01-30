#include "searchFile.h"

FilesList lscwd(const char *FilePath)
{
    WIN32_FIND_DATAA find_data;
    HANDLE file_handle;
    FilesList list_of_files = {NULL, 0};

    file_handle = FindFirstFileA(FilePath, &find_data);

    if (file_handle == INVALID_HANDLE_VALUE)
    {
        fprintf(stderr, "Could not load directory");
        return list_of_files;
    }

    do
    {
        if (find_data.cFileName[0] == '.')
            continue;
            
        char **tmp = realloc(list_of_files.names, (list_of_files.count + 1) * sizeof(char *));
        if (!tmp) break;

        list_of_files.names = tmp;

        list_of_files.names[list_of_files.count] = malloc(strlen(find_data.cFileName));
        if (!list_of_files.names[list_of_files.count]) break;

        strcpy(list_of_files.names[list_of_files.count], find_data.cFileName);
        list_of_files.count ++;
    }
    while (FindNextFileA(file_handle, &find_data));

    FindClose(file_handle);
    return list_of_files;
}

int main(void)
{
    FilesList files = lscwd("C:\\Users\\*");

    for (size_t i = 0; i < files.count; i++)
        printf("%s\n", files.names[i]);

    return 0;
}
