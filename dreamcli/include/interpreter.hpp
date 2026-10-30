#pragma once

#include <cstddef>
#include <iosfwd>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

#include "ast.hpp"
#include "commands_stream.hpp"
#include "environment.hpp"
#include "token.hpp"
#include "value.hpp"

/**
 * An error raised while executing a parsed DreamScript program.
 *
 * Runtime errors carry the source location of the token that caused them so
 * the command-line driver can report `file:line:column`.
 */
class RuntimeError : public std::runtime_error {
public:
    RuntimeError(const Token& token, const std::string& message);
    RuntimeError(std::size_t line, std::size_t column,
                 const std::string& message);

    std::size_t line() const noexcept;
    std::size_t column() const noexcept;

private:
    std::size_t line_;
    std::size_t column_;
};

/**
 * Tree-walk evaluator for DreamScript.
 *
 * The interpreter owns the global environment and executes statements in
 * order. Expressions produce `Value` objects, while command statements are
 * expanded into command arguments and dispatched through CommandDispatcher.
 */
class Interpreter {
public:
    Interpreter(std::istream& input, std::ostream& output);

    void execute(const Program& program);

private:
    std::istream& input_;
    std::ostream& output_;

    std::shared_ptr<Environment> globals_;
    std::shared_ptr<Environment> environment_;
    dreamcli::commands::CommandDispatcher dispatcher_;

    void executeStatement(const Statement& statement);
    void executeBlock(const BlockStatement& block);
    void executeCommand(const CommandStatement& command);

    Value evaluate(const Expression& expression);
    Value evaluateLiteral(const LiteralExpression& expression);
    Value evaluateUnary(const UnaryExpression& expression);
    Value evaluateBinary(const BinaryExpression& expression);

    Value readVariable(const Token& token) const;
    std::string readEnvironmentVariable(const Token& token) const;

    std::string commandName(const CommandStatement& command) const;
    std::vector<dreamcli::commands::CommandArgument> commandArguments(
        const CommandStatement& command) const;
    std::string commandWordText(const CommandWord& word) const;

    [[noreturn]] void fail(const Token& token,
                           const std::string& message) const;
};
