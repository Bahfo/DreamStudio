#include "interpreter.hpp"

#include <cctype>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <utility>

namespace {

bool isComparisonOperator(TokenType type) {
    return type == TokenType::GREATER || type == TokenType::GREATER_EQUAL ||
           type == TokenType::LESS || type == TokenType::LESS_EQUAL;
}

}  // namespace

RuntimeError::RuntimeError(const Token& token, const std::string& message)
    : std::runtime_error(message), line_(token.line), column_(token.column) {}

RuntimeError::RuntimeError(std::size_t line, std::size_t column,
                           const std::string& message)
    : std::runtime_error(message), line_(line), column_(column) {}

std::size_t RuntimeError::line() const noexcept {
    return line_;
}

std::size_t RuntimeError::column() const noexcept {
    return column_;
}

Interpreter::Interpreter(std::istream& input, std::ostream& output)
    : input_(input),
      output_(output),
      globals_(std::make_shared<Environment>()),
      environment_(globals_),
      dispatcher_() {}

void Interpreter::execute(const Program& program) {
    environment_ = globals_;

    for (const StatementPtr& statement : program.statements) {
        executeStatement(*statement);
    }
}

void Interpreter::executeStatement(const Statement& statement) {
    if (const auto* assignment =
            dynamic_cast<const AssignStatement*>(&statement)) {
        environment_->assign(assignment->target.value,
                             evaluate(*assignment->value));
        return;
    }

    if (const auto* command = dynamic_cast<const CommandStatement*>(&statement)) {
        executeCommand(*command);
        return;
    }

    if (const auto* block = dynamic_cast<const BlockStatement*>(&statement)) {
        executeBlock(*block);
        return;
    }

    if (const auto* conditional = dynamic_cast<const IfStmt*>(&statement)) {
        if (evaluate(*conditional->condition).asBoolean()) {
            executeBlock(*conditional->thenBranch);
        } else if (conditional->elseBranch) {
            executeBlock(*conditional->elseBranch);
        }
        return;
    }

    if (const auto* loop = dynamic_cast<const WhileStmt*>(&statement)) {
        while (evaluate(*loop->condition).asBoolean()) {
            executeBlock(*loop->body);
        }
        return;
    }

    throw std::runtime_error("Unsupported statement type.");
}

void Interpreter::executeBlock(const BlockStatement& block) {
    std::shared_ptr<Environment> previous = environment_;
    environment_ = std::make_shared<Environment>(previous);

    try {
        for (const StatementPtr& statement : block.statements) {
            executeStatement(*statement);
        }
    } catch (...) {
        environment_ = previous;
        throw;
    }

    environment_ = previous;
}

void Interpreter::executeCommand(const CommandStatement& command) {
    dreamcli::commands::CommandContext context{input_, output_, *environment_};

    try {
        dispatcher_.execute(commandName(command), commandArguments(command),
                            context);
    } catch (const dreamcli::commands::CommandError& error) {
        fail(command.name, error.what());
    }
}

Value Interpreter::evaluate(const Expression& expression) {
    if (const auto* literal =
            dynamic_cast<const LiteralExpression*>(&expression)) {
        return evaluateLiteral(*literal);
    }

    if (const auto* unary = dynamic_cast<const UnaryExpression*>(&expression)) {
        return evaluateUnary(*unary);
    }

    if (const auto* binary = dynamic_cast<const BinaryExpression*>(&expression)) {
        return evaluateBinary(*binary);
    }

    throw std::runtime_error("Unsupported expression type.");
}

Value Interpreter::evaluateLiteral(const LiteralExpression& expression) {
    const Token& token = expression.token;

    switch (token.type) {
        case TokenType::NUMBER:
            try {
                return Value(std::stod(token.value));
            } catch (const std::exception&) {
                fail(token, "Invalid number '" + token.value + "'.");
            }
        case TokenType::STRING:
            return Value(token.value);
        case TokenType::TRUE:
            return Value(true);
        case TokenType::FALSE:
            return Value(false);
        case TokenType::VARIABLE:
            return readVariable(token);
        case TokenType::ENV_VARIABLE:
            return Value(readEnvironmentVariable(token));
        default:
            fail(token, "Expected a literal expression.");
    }
}

Value Interpreter::evaluateUnary(const UnaryExpression& expression) {
    const Value operand = evaluate(*expression.operand);

    switch (expression.op.type) {
        case TokenType::NOT:
            return Value(!operand.asBoolean());
        case TokenType::MINUS:
            if (!operand.isNumber()) {
                fail(expression.op,
                     "Unary '-' expects a number, but got " +
                         operand.typeName() + ".");
            }
            return Value(-operand.asNumber());
        case TokenType::PLUS:
            if (!operand.isNumber()) {
                fail(expression.op,
                     "Unary '+' expects a number, but got " +
                         operand.typeName() + ".");
            }
            return operand;
        default:
            fail(expression.op, "Unsupported unary operator.");
    }
}

Value Interpreter::evaluateBinary(const BinaryExpression& expression) {
    if (expression.operand.type == TokenType::AND) {
        const Value left = evaluate(*expression.left);
        if (!left.asBoolean()) {
            return Value(false);
        }
        return Value(evaluate(*expression.right).asBoolean());
    }

    if (expression.operand.type == TokenType::OR) {
        const Value left = evaluate(*expression.left);
        if (left.asBoolean()) {
            return Value(true);
        }
        return Value(evaluate(*expression.right).asBoolean());
    }

    const Value left = evaluate(*expression.left);
    const Value right = evaluate(*expression.right);

    if (expression.operand.type == TokenType::EQUAL_EQUAL) {
        return Value(left.equals(right));
    }

    if (expression.operand.type == TokenType::BANG_EQUAL) {
        return Value(!left.equals(right));
    }

    if (isComparisonOperator(expression.operand.type)) {
        if (left.isNumber() && right.isNumber()) {
            const double a = left.asNumber();
            const double b = right.asNumber();

            switch (expression.operand.type) {
                case TokenType::GREATER:
                    return Value(a > b);
                case TokenType::GREATER_EQUAL:
                    return Value(a >= b);
                case TokenType::LESS:
                    return Value(a < b);
                case TokenType::LESS_EQUAL:
                    return Value(a <= b);
                default:
                    break;
            }
        }

        if (left.isString() && right.isString()) {
            const std::string& a = left.asString();
            const std::string& b = right.asString();

            switch (expression.operand.type) {
                case TokenType::GREATER:
                    return Value(a > b);
                case TokenType::GREATER_EQUAL:
                    return Value(a >= b);
                case TokenType::LESS:
                    return Value(a < b);
                case TokenType::LESS_EQUAL:
                    return Value(a <= b);
                default:
                    break;
            }
        }

        fail(expression.operand,
             "Cannot compare " + left.typeName() + " with " +
                 right.typeName() + ".");
    }

    if (expression.operand.type == TokenType::PLUS) {
        if (left.isString() || right.isString()) {
            return Value(left.toString() + right.toString());
        }
        if (left.isNumber() && right.isNumber()) {
            return Value(left.asNumber() + right.asNumber());
        }
        fail(expression.operand,
             "Operator '+' cannot be applied to " + left.typeName() +
                 " and " + right.typeName() + ".");
    }

    if (!left.isNumber() || !right.isNumber()) {
        fail(expression.operand,
             "Operator '" + expression.operand.value +
                 "' expects numbers, but got " + left.typeName() + " and " +
                 right.typeName() + ".");
    }

    const double a = left.asNumber();
    const double b = right.asNumber();

    switch (expression.operand.type) {
        case TokenType::MINUS:
            return Value(a - b);
        case TokenType::STAR:
            return Value(a * b);
        case TokenType::SLASH:
            if (b == 0.0) {
                fail(expression.operand, "Division by zero.");
            }
            return Value(a / b);
        case TokenType::PERCENT:
            if (b == 0.0) {
                fail(expression.operand, "Modulo by zero.");
            }
            return Value(std::fmod(a, b));
        default:
            fail(expression.operand, "Unsupported binary operator.");
    }
}

Value Interpreter::readVariable(const Token& token) const {
    const Value* value = environment_->find(token.value);

    if (value == nullptr) {
        fail(token, "Undefined variable '$" + token.value + "'.");
    }

    return *value;
}

std::string Interpreter::readEnvironmentVariable(const Token& token) const {
    const char* value = std::getenv(token.value.c_str());
    return value == nullptr ? std::string() : std::string(value);
}

std::string Interpreter::commandName(const CommandStatement& command) const {
    std::string name;

    for (const Token& part : command.nameParts) {
        name += part.lexeme.empty() ? part.value : part.lexeme;
    }

    return name;
}

std::vector<dreamcli::commands::CommandArgument> Interpreter::commandArguments(
    const CommandStatement& command) const {
    std::vector<dreamcli::commands::CommandArgument> arguments;
    arguments.reserve(command.arguments.size());

    for (const CommandWord& word : command.arguments) {
        dreamcli::commands::CommandArgument argument;

        if (word.parts.size() == 1 &&
            word.parts.front().type == TokenType::VARIABLE) {
            const std::string& variable = word.parts.front().value;
            const Value* existing = environment_->find(variable);

            argument.variable = variable;
            argument.text = existing == nullptr ? std::string()
                                                : existing->toString();
        } else {
            argument.text = commandWordText(word);
        }

        arguments.push_back(std::move(argument));
    }

    return arguments;
}

std::string Interpreter::commandWordText(const CommandWord& word) const {
    std::string text;

    for (const Token& part : word.parts) {
        switch (part.type) {
            case TokenType::STRING:
                text += part.value;
                break;
            case TokenType::VARIABLE:
                text += readVariable(part).toString();
                break;
            case TokenType::ENV_VARIABLE:
                text += readEnvironmentVariable(part);
                break;
            case TokenType::TRUE:
                text += "true";
                break;
            case TokenType::FALSE:
                text += "false";
                break;
            default:
                text += part.lexeme.empty() ? part.value : part.lexeme;
                break;
        }
    }

    return text;
}

void Interpreter::fail(const Token& token, const std::string& message) const {
    throw RuntimeError(token, message);
}
