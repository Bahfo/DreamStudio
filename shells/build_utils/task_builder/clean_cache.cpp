#include <vector>
#include <string>
#include <iostream>
#include <algorithm>
#include <filesystem>

namespace fs = std::filesystem;

const std::vector<std::string> CACHE_EXTENSIONS = {".tmp", ".temp", ".log", ".bak", ".old"};
const std::vector<std::string> CACHE_FOLDERS = {"__pycache__", ".pytest_cache", "node_modules", ".cache"};
const std::vector<std::string> OS_JUNK_FILES = {".DS_Store", "Thumbs.db"};

bool should_delete(const fs::directory_entry& entry)
{
    std::string name = entry.path().filename().string();
    std::string extn = entry.path().extension().string();

    if (entry.is_directory())
    {
        return std::find(CACHE_FOLDERS.begin(), CACHE_FOLDERS.end(), name) != CACHE_FOLDERS.end();
    }

    if (std::find(CACHE_EXTENSIONS.begin(), CACHE_EXTENSIONS.end(), extn) != CACHE_EXTENSIONS.end())
    {
        return true;
    }

    if (std::find(OS_JUNK_FILES.begin(), OS_JUNK_FILES.end(), name) != OS_JUNK_FILES.end())
    {
        return true;
    }

    return false;
}

void clean_directory(const fs::path& target_path)
{
    if (!fs::exists(target_path) || !fs::is_directory(target_path))
    {
        std::cerr << "Error: Path does not exist, or is not a directory." << std::endl;
        return;
    }

    std::cout << "Preparing for Build: Cleaning ..." << std::endl;

    std::vector<fs::path> paths_to_remove;

    try 
    {
        for (const auto& entry : fs::recursive_directory_iterator(target_path))
        {
            if (should_delete(entry))
            {
                paths_to_remove.push_back(entry.path());
            }
        }

        for (const auto& p : paths_to_remove)
        {
            std::cout << "Removing: " << p << std::endl;
            fs::remove_all(p);
        }
    }
    catch (const fs::filesystem_error& error)
    {
        std::cerr << "Build Failed: Cleaning Failed: " << error.what() << std::endl;
    } 

    std::cout << "Build Stage 1 Finished: Cleanup" << std::endl;
}

int main(int argc, char* argv[]) {
    std::string path_str = (argc > 1) ? argv[1] : ".";
    clean_directory(path_str);
    return 0;
}