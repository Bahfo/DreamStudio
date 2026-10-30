#pragma once

#include <functional>
#include <iosfwd>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

#include "environment.hpp"

namespace dreamcli::commands {

/**
 * Raised by a command when it cannot complete.
 *
 * The interpreter catches this type and attaches the source location of the
 * command before reporting it to the user.
 */
class CommandError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

/**
 * One already-expanded command argument.
 *
 * `text` is the value a command should normally consume. `variable` is set
 * only when the argument was written as exactly one `$variable`, which lets
 * commands such as `input` write back into the caller's variable. For such an
 * argument, an unset variable produces empty `text` instead of an error.
 */
struct CommandArgument {
    std::string text;
    std::optional<std::string> variable;
};

/**
 * Runtime services made available to every command implementation.
 */
struct CommandContext {
    std::istream& input;
    std::ostream& output;
    Environment& environment;
};

using CommandHandler =
    std::function<void(CommandContext&, const std::vector<CommandArgument>&)>;

struct CommandDefinition {
    std::string_view name;
    CommandHandler handler;
};

/**
 * The central DreamScript command manifest.
 *
 * To add a command:
 *   1. Declare its handler above this function, for example:
 *        void ExampleCommand(CommandContext&,
 *                            const std::vector<CommandArgument>&);
 *   2. Add one `{"name", &Handler},` entry below.
 *   3. Implement the handler in `src/commands/<name>.cpp`.
 *
 * The dispatcher lowercases both the manifest name and the caller's command
 * name, so `print`, `Print` and `PRINT` are equivalent. Arguments and
 * variables are not case-folded.
 *
 * No commands are registered yet.
 */
inline const std::vector<CommandDefinition>& commandStream() {
    static const std::vector<CommandDefinition> commands = {
        // {"example", &ExampleCommand},
    };

    return commands;
}

/**
 * Case-insensitive command lookup and execution.
 *
 * `handler.cpp` builds the lookup table from `commandStream()`. Commands can
 * also be registered explicitly through `registerCommand`.
 */
class CommandDispatcher {
public:
    CommandDispatcher();

    void registerCommand(const std::string& name, CommandHandler handler);

    void execute(const std::string& name,
                 const std::vector<CommandArgument>& arguments,
                 CommandContext& context) const;

private:
    std::unordered_map<std::string, CommandHandler> handlers_;
};

}  // namespace dreamcli::commands
