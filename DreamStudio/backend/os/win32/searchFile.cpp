#ifdef _WIN32
#include "searchFile.hpp"
#include <windows.h>

#ifdef __cplusplus
    extern "C"
    {
        #endif
        // The following is win32 API calls
        // Not implemented yet in POSIX systems, acceptance of any participants
        // to complete this mess in posix systems and windows systems too.
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

                list_of_files.names[list_of_files.count] = malloc(strlen(find_data.cFileName) + 1);
                if (!list_of_files.names[list_of_files.count]) break;

                strcpy(list_of_files.names[list_of_files.count], find_data.cFileName);
                list_of_files.count ++;
            }
            while (FindNextFileA(file_handle, &find_data));

            FindClose(file_handle);
            return list_of_files;
        }

        const char *getFilesExtensions(const char *filename)
        {
            const char *dot = strrchr(filename, '.');
            if (!dot || dot == filename) return NULL;

            return dot + 1;
        }

        FilesType scancwd(const FilesList *FilePath)
        {
            FilesType files = {NULL, NULL, 0};
            files.count = FilePath -> count;

            files.file_extn = malloc(files.count * sizeof(char *));
            files.file_name = malloc(files.count * sizeof(char *));

            if (!files.file_extn || !files.file_name)
            {
                free(files.file_extn);
                free(files.file_name);
                files.count = 0;
                return files;
            }

            for (size_t i = 0; i < files.count; i++)
            {
                const char *extension = getFilesExtensions(FilePath->names[i]);
                files.file_name[i] = FilePath->names[i];
                if (extension)
                {
                    files.file_extn[i] = strdup(extension);
                }
                else
                {
                    files.file_extn[i] = NULL;
                }
            }
            return files;
        }

        int extensionCode(const char *extension)
        {
            if (!extension) return 0;
            if (strcmp(extension, "c") == 0) return 1;
            if (strcmp(extension, "h") == 0) return 2;
            if (strcmp(extension, "cpp") == 0) return 3;
            if (strcmp(extension, "hpp") == 0) return 4;
            if (strcmp(extension, "py") == 0) return 5;
            if (strcmp(extension, "pyc") == 0) return 6;
            if (strcmp(extension, "exe") == 0) return 7;
            if (strcmp(extension, "txt") == 0) return 8;
            return -1;
        }

        void ensureCapacity(DirectorySummary *summary)
        {
            if (summary->count >= summary->capacity)
            {
                size_t newCapacity = summary->capacity == 0 ? 64 : summary->capacity * 2;

                summary->name = realloc(summary->name, newCapacity * sizeof(char *));
                summary->extn = realloc(summary->extn, newCapacity * sizeof(char *));
                summary->path = realloc(summary->path, newCapacity * sizeof(char *));
                summary->lang = realloc(summary->lang, newCapacity * sizeof(char *));

                summary->capacity = newCapacity;
            }
        }

        void scanDirectoryRecursive(const char *dirPath, DirectorySummary *summary)
        {
            WIN32_FIND_DATAA find_data;
            HANDLE file_handle;
            char searchPath[MAX_PATH];

            snprintf(searchPath, MAX_PATH, "%s\\*", dirPath);

            file_handle = FindFirstFileA(searchPath, &find_data);
            if (file_handle == INVALID_HANDLE_VALUE) return;

            do
            {
                if (strcmp(find_data.cFileName, ".") == 0 || strcmp(find_data.cFileName, "..") == 0)
                    continue;

                char fullPath[MAX_PATH];
                snprintf(fullPath, MAX_PATH, "%s\\%s", dirPath, find_data.cFileName);

                if (find_data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)
                {
                    scanDirectoryRecursive(fullPath, summary);
                }
                else
                {
                    ensureCapacity(summary);

                    size_t i = summary->count;

                    summary->name[i] = strdup(find_data.cFileName);
                    summary->path[i] = strdup(fullPath);

                    const char *ext = getFilesExtensions(find_data.cFileName);
                    summary->extn[i] = ext ? strdup(ext) : strdup("");

                    switch (extensionCode(ext))
                    {
                        case 0: summary->lang[i] = strdup("Unknown"); break;
                        case 1: summary->lang[i] = strdup("C Language"); break;
                        case 2: summary->lang[i] = strdup("C Header"); break;
                        case 3: summary->lang[i] = strdup("C++ Language"); break;
                        case 4: summary->lang[i] = strdup("C++ Header"); break;
                        case 5: summary->lang[i] = strdup("Python Script"); break;
                        case 6: summary->lang[i] = strdup("Python Compiled"); break;
                        case 7: summary->lang[i] = strdup("Executable"); break;
                        case 8: summary->lang[i] = strdup("Text File"); break;
                        default: summary->lang[i] = strdup("Unknown"); break;
                    }
                    summary->count++;
                }

            } while (FindNextFileA(file_handle, &find_data));

            FindClose(file_handle);
        }

        void freelist(FilesList *list)
        {
            for (size_t i = 0; i < list->count; i++)
                free(list->names[i]);

            free(list->names);
            list->names = NULL;
            list->count = 0;
        }

        void freeextn(FilesType *list)
        {
            for (size_t i = 0; i < list->count; i++)
            {
                free(list->file_extn[i]);
            }

            free(list->file_extn);
            free(list->file_name);
            list->file_extn = NULL;
            list->file_name = NULL;
            list->count = 0;
        }

        void freeTable(DirectorySummary *table)
        {
            for (size_t i = 0; i < table->count; i++)
            {
                free(table->extn[i]);
                free(table->lang[i]);
                free(table->name[i]);
                free(table->path[i]);
            }

            free(table->extn);
            free(table->lang);
            free(table->name);
            free(table->path);

            table->extn = NULL;
            table->lang = NULL;
            table->name = NULL;
            table->path = NULL;
            table->count = 0;
            table->prcnt = 0.0;
            table->capacity = 0;
        }
        #ifdef __cplusplus
    }
    #endif
#endif