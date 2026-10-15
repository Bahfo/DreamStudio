#pragma once

#include <cstddef>
#include <memory>
#include <string>
#include <vector>

#include "ast.hpp"
#include "token.hpp"


class Parser {
public:
    explicit Parser(const std::vector<Token>& tokens);
    Program parse();
private:
    const std::vector<Token> &tokens;
    std::size_t current_ = 0;

    const Token& peek() const;
    const Token& advance();

    bool check(TokenType type) const;
    bool checkNext(TokenType type) const;
    bool isAtEnd() const;
    bool match(TokenType type);

    const Token& consume(TokenType type, const std::string& message);

    [[noreturn]] void fail(const std::string& message) const;

    void skipSeparators();
    void skipNewlines();
    bool nextIsAfterNewlines(TokenType type) const;

    StatementPtr parseStatement();
    StatementPtr parseAssignment();
    StatementPtr parseCommand();

    std::unique_ptr<BlockStatement> parseBlock();
    StatementPtr parseIf();
    StatementPtr parseWhile();

    ExpressionPtr parseExpression();
    ExpressionPtr parseOr();
    ExpressionPtr parseAnd();
    ExpressionPtr parseEquality();
    ExpressionPtr parseComparison();
    ExpressionPtr parseTerm();
    ExpressionPtr parseFactor();
    ExpressionPtr parseUnary();
    ExpressionPtr parsePrimary();
};