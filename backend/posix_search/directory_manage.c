#include <stdio.h>
#include <dirent.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>

void clear_cache_directory(const char *path) {
    DIR *dir;
    struct dirent *de;
    
    // Open the directory
    dir = opendir(path);
    if (dir == NULL) {
        perror("Could not open directory");
        return;
    }

    // Iterate over all entries in the directory
    while ((de = readdir(dir)) != NULL) {
        // Skip the "." and ".." entries to prevent issues or infinite loops
        if (strcmp(de->d_name, ".") == 0 || strcmp(de->d_name, "..") == 0) {
            continue;
        }

        // Construct the full path of the entry
        char full_path[1024];
        snprintf(full_path, sizeof(full_path), "%s/%s", path, de->d_name);

        // Use unlink() to remove the file
        // For subdirectories, a recursive approach would be needed using rmdir() 
        // for empty directories, or a function like nftw() for recursive deletion.
        if (unlink(full_path) == 0) {
            printf("Removed: %s\n", full_path);
        } else {
            perror("Failed to remove file/directory");
            // If the entry is a directory and not a file, unlink will fail.
            // A check for file type can be added to handle directories appropriately.
        }
    }

    // Close the directory stream
    closedir(dir);
}

int main() {
    const char *cache_dir_path = "./my_cache"; // Replace with your directory path
    clear_cache_directory(cache_dir_path);
    return 0;
}
