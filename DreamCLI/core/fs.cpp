#include "fs.hpp"

string format_permissions(fs::perms permissions) {
    if (permissions == fs::perms::unknown) return "?????????";
    string result;

    for (const auto &[bit, symbol] : FileOperations::PERMISSION_BITS) {
        if ((permissions & bit) != fs::perms::none) result += symbol;
        else result += '-';
    }

    return result;
}

std::optional<fs::path> GetCurrentDirectory() {
    try {
        return fs::current_path();
    } catch (const fs::filesystem_error&) {
        return std::nullopt; 
    }
}

std::vector<string> ListFiles(const Arguments &args) {
    string help = R"(
    Command: List-Items
    Usage: List-Items <OPTIONS> <PATH>
    Options: --help, -h, --long, -l

    Lists files and subdirectories of a given directory path.

    Arguments: 
        PATH:       Path to specified directory, provided that path is correct.
        OPTIONS:    A set of paramaters (options)
            --help, -h      Display help
            --long, -l      Shows detailed item information
    Examples:
        List-Items
        List-Items /home/user/Desktop
        List-Items -l /home/user/Desktop
        List-Items --help
    )";

    fs::path target = ".";
    bool long_format = false;
    bool path_provided = false;
    bool options_enabled = true;
}


void main() {
    GetCurrentDirectory()
    string value;
    std::vector<string> value;
