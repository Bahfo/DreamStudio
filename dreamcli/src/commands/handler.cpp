/**
 * Commands handler inside DreamCLI
 *
 * (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
 * This module is licensed under the GPLv3 License. Read LICENSE
 * for more info.
 */

#include "commands_stream.hpp"

#include <cctype>
#include <string>
#include <utility>

namespace dreamcli::commands {

namespace {

std::string normalizeName(const std::string& name) {
    std::string normalized;
    normalized.reserve(name.size());

    for (char character : name) {
        normalized += static_cast<char>(
            std::tolower(static_cast<unsigned char>(character)));
    }

    return normalized;
}

}  // namespace

CommandDispatcher::CommandDispatcher() {
    for (const CommandDefinition& definition : commandStream()) {
        registerCommand(std::string(definition.name), definition.handler);
    }
}

void CommandDispatcher::registerCommand(const std::string& name,
                                        CommandHandler handler) {
    handlers_.insert_or_assign(normalizeName(name), std::move(handler));
}

void CommandDispatcher::execute(
    const std::string& name,
    const std::vector<CommandArgument>& arguments,
    CommandContext& context) const {
    const auto found = handlers_.find(normalizeName(name));

    if (found == handlers_.end()) {
        std::string message = "Unknown command '" + name + "'.";
        if (handlers_.empty()) {
            message += " No commands are registered yet.";
        }
        throw CommandError(message);
    }

    found->second(context, arguments);
}

}  // namespace dreamcli::commands
