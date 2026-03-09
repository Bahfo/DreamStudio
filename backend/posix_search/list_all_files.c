#include <stdio.h>
#include <stdlib.h>
#include <dirent.h>

int list_all_files(char* directory[])
{
    DIR *dir;
    struct dirent *ent;
    if ((dir = opendir(&directory) != NULL))
    {
        while ((ent = readdir(dir)) != NULL)
        {
            printf("%s\n", ent -> d_name);
        }
        closedir (dir);
    }
    else
    {
        perror("");
        return EXIT_FAILURE;
    }
}
