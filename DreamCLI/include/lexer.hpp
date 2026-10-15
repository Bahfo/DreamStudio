#pragma once

#include <cstddef>
#include <string>
#include <vector>

#include "token.hpp"

class Lexer {
public:
    explicit Lexer(std::string source);
    std::vector<Token> tokenize();

private:
    std::string source_;

    std::size_t position_ = 0;
    std::size_t line_ = 1;
    std::size_t column_ = 1;

    bool isAtEnd() const;
    char peek() const;
    char peekNext() const;
    char advance();
    bool match(char expected);

    [[noreturn]] void fail(const std::string& message, std::size_t line,
                           std::size_t column) const;
    Token makeToken(TokenType type, std::string value, std::size_t line,
                    std::size_t column) const;

    void skipWhitespace();
    void skipComment();

    Token lexString();
    Token lexNumber();
    Token lexIdentifierOrKeyword();
    Token lexVariable();
    Token lexSymbol();

    static bool isAlpha(char c);
    static bool isDigit(char c);
    static bool isAlphaNumeric(char c);
    static std::string toLower(const std::string& text);
};
