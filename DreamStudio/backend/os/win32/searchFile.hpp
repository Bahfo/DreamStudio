// CORYRIGHT 2026 DREAMSTUDIO - WRITTEN BY BAHAA NOFAL

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

    //Checks if a given path is a file or not.
    //If true, it checks its extension and prints it out.
    const char *getFilesExtensions(const char *filename);

    //Scans the current working directory to return a list of
    //files and directories names, and their extensions if any.
    FilesType scancwd(const FilesList *FilePath);

    //maps each extension, from a list of extensions, to its
    //integer code so it can be used inside switch-cases
    int extensionCode(const char *extension);

    //Ensure the struct `Directory Summary` has enough space
    //capacity to hold the values of the structure, by reallocation.
    void ensureCapacity(DirectorySummary *summary);

    //Recursively scans a directory and its subdirectories to check
    //files path, extensions, and type, and scan directories path and name.
    void scanDirectoryRecursive(const char *dirPath, DirectorySummary *smmary);

    //Ignores files handled after recursive scans
    //Example of ignored files: Cached files, executables, etc.
    void ignoreListofFiles(DirectorySummary *list_of_files);

    //Free allocation of a FileList struct
    void freelist(FilesList *list);

    //Free allocation of a FileType struct
    void freeextn(FilesType *list);

    //Free allocation of a DirectorySummary struct
    void freeTable(DirectorySummary *table);

#endif
