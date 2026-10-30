#pragma once

#include <memory>
#include <vector>

#include "token.hpp"

struct Expression {
    virtual ~Expression() = default;
};

struct Statement {
    virtual ~Statement() = default;
};

using ExpressionPtr = std::unique_ptr<Expression>;
using StatementPtr = std::unique_ptr<Statement>;

struct LiteralExpression : Expression {
    Token token;
};

struct UnaryExpression : Expression {
    Token op;
    ExpressionPtr operand;
};

struct BinaryExpression : Expression {
    ExpressionPtr left;
    Token operand;
    ExpressionPtr right;
};

struct AssignStatement : Statement {
    Token target;
    ExpressionPtr value;
};

struct CommandWord {
    std::vector<Token> parts;
};

struct CommandStatement : Statement {
    Token name;
    std::vector<Token> nameParts;
    std::vector<CommandWord> arguments;
};

struct BlockStatement : Statement {
    Token openingBrace;
    std::vector<StatementPtr> statements;
};

struct IfStmt : Statement {
    Token keyword;
    ExpressionPtr condition;

    std::unique_ptr<BlockStatement> thenBranch;
    std::unique_ptr<BlockStatement> elseBranch;
};

struct WhileStmt : Statement {
    Token keyword;
    ExpressionPtr condition;
    std::unique_ptr<BlockStatement> body;
};

struct Program {
    std::vector<StatementPtr> statements;
};
