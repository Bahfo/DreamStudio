/**
 * Commands handler inside DreamCLI
 * 
 * (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
 * This module is licensed under the GPLv3 License. Read LICENSE 
 * for more info.
 */

#include "fs.hpp"

std::vector<string> parse_commands(const string &command_line) {
    std::vector<string> tokens;
    string current;
    bool in_quotes = false;

    for (size_t i = 0; i < command_line.size(); ++i) {
        char c = command_line[i];
        if (c == '"') in_quotes = !in_quotes;
        else if (c == ' ' && !in_quotes) {
            if (!current.empty()) {
                tokens.push_back(current);
                current.clear();
            }
        } else current += c;
    }

    if (!current.empty()) tokens.push_back(current);
    return tokens;
}

int commandsHandler(const string &line) {
    std::unordered_map<string, CommandHandler> commands;
    bool running = true;

    commands.emplace("List-Items", [](const Arguments &path) {
        
    });
}