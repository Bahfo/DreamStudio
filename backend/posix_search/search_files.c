#include <stdio.h>
#include <stdlib.h>
#include <dirent.h>
#include <string.h>
#include <sys/stat.h>

void listFiles(const char *path)
{
    struct dirent *entry;
    DIR *direct_ptr = opendir(path);
    if (direct_ptr == NULL)
    {
        perror("opendir");
        return;
    }

    while ((entry = readdir(direct_ptr)) != NULL)
    {
        // Skip current and parent directory entries
        if (strcmp(entry -> d_name, ".") == 0 || strcmp(entry -> d_name, "..") == 0)
            continue;
        printf("%s/%s\n", path, entry -> d_name);

        // Build the new path for the directory entry
        char newPath[1024]; // Buffer
        snprintf(newPath, sizeof(newPath), "%s/%s", path, entry -> d_name);

        // Checking if the entry is a directory
        struct stat statbuf;
        if (stat(newPath, &statbuf) == 0 && S_ISDIR(statbuf.st_mode))
        {
            listFiles(newPath);
        }

        closedir(direct_ptr);
    }
}

int main()
{
    listFiles(".");
    return 0;
}