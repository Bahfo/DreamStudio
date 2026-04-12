#include <stdio.h>
#include <dirent.h>
#include <unistd.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif

void clear_cache_directory(const char *path) {
    DIR *dir;
    struct dirent *de;
    
    dir = opendir(path);
    if (dir == NULL) {
        perror("Could not open directory");
        return;
    }

    while ((de = readdir(dir)) != NULL) {
        if (strcmp(de->d_name, ".") == 0 || strcmp(de->d_name, "..") == 0) {
            continue;
        }

        char full_path[1024];
        snprintf(full_path, sizeof(full_path), "%s/%s", path, de->d_name);

        if (unlink(full_path) == 0) {
            printf("Removed: %s\n", full_path);
        } else {
            // Note: unlink() fails on directories on most systems.
            perror("Failed to remove");
        }
    }

    closedir(dir);
}

#ifdef __cplusplus
}
#endif

int main() {
    const char *cache_dir_path = "./my_cache"; 
    clear_cache_directory(cache_dir_path);
    return 0;
}