#include <stdio.h>
#include <stdlib.h>
#include <dirent.h>
#include <string.h>
#include <sys/stat.h>

#ifdef __cplusplus
extern "C" {
#endif

void listFiles(const char *path) {
    struct dirent *entry;
    DIR *direct_ptr = opendir(path);
    
    if (direct_ptr == NULL) {
        perror("opendir");
        return;
    }

    while ((entry = readdir(direct_ptr)) != NULL) {
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0)
            continue;

        char newPath[1024];
        snprintf(newPath, sizeof(newPath), "%s/%s", path, entry->d_name);
        printf("%s\n", newPath);

        struct stat statbuf;
        if (stat(newPath, &statbuf) == 0 && S_ISDIR(statbuf.st_mode)) {
            listFiles(newPath); // Recursive call
        }
    }

    closedir(direct_ptr);
}

#ifdef __cplusplus
}
#endif