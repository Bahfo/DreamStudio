/**
 * Filesystem header file for fs operations to support DreamCLI.
 * 
 * (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
 * This module is licensed under the GPLv3 License. Read LICENSE 
 * for more info.
 */

#ifndef FS_H
#define FS_H

#include <vector>
#include <cstddef>
#include <optional>
#include <iostream>
#include <functional>
#include <filesystem>
#include <unordered_map>

#define string std::string

namespace fs = std::filesystem;

using Arguments = std::vector<string>;
using CommandHandler = std::function<void(const Arguments&)>;

/**
 * Mini tokenizer from main lexer to parse command lines. 
 * Separates the command from its arguments and flags. */
std::vector<string> parse_commands(const string &command_line);

/**
 * Commands handler actions for DreamCLI.
 */
int commandsHandler();

namespace FileOperations {

const std::pair<fs::perms, string> PERMISSION_BITS[] = {
    {fs::perms::owner_read, "Owner-Read"},
    {fs::perms::owner_write, "Owner-Write"},
    {fs::perms::owner_exec, "Owner-Execute"},
    {fs::perms::group_read, "Group-Read"},
    {fs::perms::group_write, "Group-Write"},
    {fs::perms::group_exec, "Group-Execute"},
    {fs::perms::others_read, "Others-Read"},
    {fs::perms::others_write, "Others-Write"},
    {fs::perms::others_exec, "Others-Execute"}
};

string format_permissions(fs::perms permissions);

std::optional<fs::path> GetCurrentDirectory();

std::vector<string> ListFiles(fs::path path);

std::optional<fs::path> ChangeDirectory(fs::path dest_path);

std::tuple<fs::path, string> CopyFile(
    fs::path src_path, 
    fs::path dest_path, 
    std::vector<string> flags
);

std::tuple<fs::path, string> MoveFile(
    fs::path src_path, 
    fs::path dest_path, 
    std::vector<string> flags
);

std::optional<fs::path> MakeFile(fs::path src_path, string flags);

std::tuple<
    fs::path, 
    fs::filesystem_error, 
    string> 
DeleteFile (fs::path src_path);

} // FileOperations Namespace

#endif