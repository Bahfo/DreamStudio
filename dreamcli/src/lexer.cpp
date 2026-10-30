#include "lexer.hpp"

#include <cctype>
#include <stdexcept>
#include <unordered_map>
#include <utility>

namespace {

const std::unordered_map<std::string, TokenType>& keywordTable() {
    static const std::unordered_map<std::string, TokenType> table = {
        {"print", TokenType::PRINT},
        {"input", TokenType::INPUT},
        {"list-items", TokenType::LIST_ITEMS},
        {"change-directory", TokenType::CHANGE_DIRECTORY},
        {"if", TokenType::IF},
        {"then", TokenType::THEN},
        {"else", TokenType::ELSE},
        {"while", TokenType::WHILE},
        {"true", TokenType::TRUE},
        {"false", TokenType::FALSE},
        {"and", TokenType::AND},
        {"or", TokenType::OR},
        {"not", TokenType::NOT},
    };
    return table;
}

bool isEnvPrefix(const std::string& text) {
    return text.size() == 3 &&
           (text[0] == 'e' || text[0] == 'E') &&
           (text[1] == 'n' || text[1] == 'N') &&
           (text[2] == 'v' || text[2] == 'V');
}

}  // namespace

Lexer::Lexer(std::string source) : source_(std::move(source)) {}

bool Lexer::isAtEnd() const {
    return position_ >= source_.size();
}

char Lexer::peek() const {
    if (isAtEnd()) return '\0';
    return source_[position_];
}

char Lexer::peekNext() const {
    if (position_ + 1 >= source_.size()) return '\0';
    return source_[position_ + 1];
}

char Lexer::advance() {
    char current = source_[position_++];
    if (current == '\n') {
        ++line_;
        column_ = 1;
    } else {
        ++column_;
    }
    return current;
}

bool Lexer::match(char expected) {
    if (isAtEnd() || source_[position_] != expected) return false;
    advance();
    return true;
}

void Lexer::fail(const std::string& message, std::size_t line,
                 std::size_t column) const {
    throw std::runtime_error(message + " at line " + std::to_string(line) +
                             ", column " + std::to_string(column) + ".");
}

Token Lexer::makeToken(TokenType type, std::string value, std::size_t line,
                       std::size_t column) const {
    std::string lexeme = source_.substr(tokenStart_, position_ - tokenStart_);
    return Token{type, std::move(value), line, column, std::move(lexeme)};
}

bool Lexer::isAlpha(char c) {
    return (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || c == '_';
}

bool Lexer::isDigit(char c) {
    return c >= '0' && c <= '9';
}

bool Lexer::isAlphaNumeric(char c) {
    return isAlpha(c) || isDigit(c);
}

std::string Lexer::toLower(const std::string& text) {
    std::string out;
    out.reserve(text.size());
    for (char c : text) {
        out += static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    }
    return out;
}

void Lexer::skipWhitespace() {
    while (!isAtEnd()) {
        char c = peek();
        if (c == ' ' || c == '\t' || c == '\r') {
            advance();
        } else {
            break;
        }
    }
}

void Lexer::skipComment() {
    while (!isAtEnd() && peek() != '\n') {
        advance();
    }
}

Token Lexer::lexString() {
    const std::size_t startLine = line_;
    const std::size_t startColumn = column_;
    const char quote = advance();
    const bool isDouble = (quote == '"');

    std::string value;
    while (!isAtEnd()) {
        char c = peek();
        if (c == '\n') {
            value += advance();
            continue;
        }
        if (c == quote) {
            advance();
            return makeToken(TokenType::STRING, value, startLine, startColumn);
        }
        if (c == '\\') {
            advance();  // consume backslash.
            if (isAtEnd()) break;
            char esc = advance();
            if (esc == '\n') continue; 
            if (isDouble) {
                switch (esc) {
                    case 'n': value += '\n'; break;
                    case 't': value += '\t'; break;
                    case 'r': value += '\r'; break;
                    case '"': value += '"'; break;
                    case '\'': value += '\''; break;
                    case '\\': value += '\\'; break;
                    case '$': value += '$'; break;
                    default: value += esc; break;
                }
            } else {
                if (esc == '\'' || esc == '\\') {
                    value += esc;
                } else {
                    value += '\\';
                    value += esc;
                }
            }
            continue;
        }
        value += advance();
    }

    fail("Unterminated string literal", startLine, startColumn);
}

Token Lexer::lexNumber() {
    const std::size_t startLine = line_;
    const std::size_t startColumn = column_;

    std::string value;
    while (!isAtEnd() && isDigit(peek())) {
        value += advance();
    }
    if (peek() == '.' && isDigit(peekNext())) {
        value += advance();  // consume '.'.
        while (!isAtEnd() && isDigit(peek())) {
            value += advance();
        }
    }
    return makeToken(TokenType::NUMBER, value, startLine, startColumn);
}

Token Lexer::lexIdentifierOrKeyword() {
    const std::size_t startLine = line_;
    const std::size_t startColumn = column_;

    std::string word;
    while (!isAtEnd() && (isAlphaNumeric(peek()))) {
        word += advance();
    }
    while (!isAtEnd() && peek() == '-' && isAlpha(peekNext())) {
        const std::size_t wordLen = word.size();
        const std::size_t savedPos = position_;
        const std::size_t savedLine = line_;
        const std::size_t savedCol = column_;
        word += advance();  // '-'.
        while (!isAtEnd() && isAlphaNumeric(peek())) {
            word += advance();
        }

        const auto& table = keywordTable();
        if (table.find(toLower(word)) != table.end()) {
            continue; 
        }

        position_ = savedPos;
        line_ = savedLine;
        column_ = savedCol;
        word.resize(wordLen);
        break;
    }

    const auto& table = keywordTable();
    auto it = table.find(toLower(word));
    if (it != table.end()) {
        return makeToken(it->second, word, startLine, startColumn);
    }
    return makeToken(TokenType::IDENTIFIER, word, startLine, startColumn);
}

Token Lexer::lexVariable() {
    const std::size_t startLine = line_;
    const std::size_t startColumn = column_;
    advance();  // consume '$'.

    if (isAtEnd()) {
        fail("Unexpected end of input after '$'", startLine, startColumn);
    }

    if (peek() == '{') {
        advance();  // consume '{'.
        std::string inner;
        while (!isAtEnd() && peek() != '}') {
            char c = peek();
            if (isAlphaNumeric(c) || c == '_' || c == ':') {
                inner += advance();
            } else {
                fail(std::string("Unexpected character '") + c +
                         "' in '${...}' variable",
                     line_, column_);
            }
        }
        if (isAtEnd()) {
            fail("Unterminated '${...}' variable", startLine, startColumn);
        }
        advance();  // consume '}'.
        if (inner.empty()) {
            fail("Empty '${...}' variable name", startLine, startColumn);
        }
        auto sep = inner.find(':');
        if (sep != std::string::npos) {
            std::string prefix = inner.substr(0, sep);
            std::string name = inner.substr(sep + 1);
            if (!isEnvPrefix(prefix) || name.empty()) {
                fail("Invalid braced variable '${" + inner + "}'", startLine,
                     startColumn);
            }
            return makeToken(TokenType::ENV_VARIABLE, name, startLine,
                             startColumn);
        }
        if (!isAlpha(inner[0])) {
            fail("Invalid braced variable '${" + inner + "}'", startLine,
                 startColumn);
        }
        return makeToken(TokenType::VARIABLE, inner, startLine, startColumn);
    }

    if (!isAlpha(peek())) {
        fail("Expected variable name after '$'", line_, column_);
    }
    std::string name;
    while (!isAtEnd() && (isAlphaNumeric(peek()))) {
        name += advance();
    }

    if (isEnvPrefix(name) && peek() == ':') {
        advance();
        if (isAtEnd() || !isAlpha(peek())) {
            fail("Expected environment variable name after '$env:'", line_,
                 column_);
        }
        std::string envName;
        while (!isAtEnd() && isAlphaNumeric(peek())) {
            envName += advance();
        }
        return makeToken(TokenType::ENV_VARIABLE, envName, startLine,
                         startColumn);
    }
    return makeToken(TokenType::VARIABLE, name, startLine, startColumn);
}

Token Lexer::lexSymbol() {
    const std::size_t startLine = line_;
    const std::size_t startColumn = column_;
    const char c = advance();

    switch (c) {
        case '(': return makeToken(TokenType::LEFT_PAREN, "(", startLine, startColumn);
        case ')': return makeToken(TokenType::RIGHT_PAREN, ")", startLine, startColumn);
        case '{': return makeToken(TokenType::LEFT_BRACE, "{", startLine, startColumn);
        case '}': return makeToken(TokenType::RIGHT_BRACE, "}", startLine, startColumn);
        case ',': return makeToken(TokenType::COMMA, ",", startLine, startColumn);
        case ';': return makeToken(TokenType::SEMICOLON, ";", startLine, startColumn);
        case ':': return makeToken(TokenType::COLON, ":", startLine, startColumn);
        case '.': return makeToken(TokenType::DOT, ".", startLine, startColumn);
        case '+': return makeToken(TokenType::PLUS, "+", startLine, startColumn);
        case '-': return makeToken(TokenType::MINUS, "-", startLine, startColumn);
        case '*': return makeToken(TokenType::STAR, "*", startLine, startColumn);
        case '%': return makeToken(TokenType::PERCENT, "%", startLine, startColumn);
        case '/': return makeToken(TokenType::SLASH, "/", startLine, startColumn);
        case '=':
            if (match('=')) return makeToken(TokenType::EQUAL_EQUAL, "==", startLine, startColumn);
            return makeToken(TokenType::ASSIGN, "=", startLine, startColumn);
        case '!':
            if (match('=')) return makeToken(TokenType::BANG_EQUAL, "!=", startLine, startColumn);
            return makeToken(TokenType::NOT, "!", startLine, startColumn);
        case '>':
            if (match('=')) return makeToken(TokenType::GREATER_EQUAL, ">=", startLine, startColumn);
            return makeToken(TokenType::GREATER, ">", startLine, startColumn);
        case '<':
            if (match('=')) return makeToken(TokenType::LESS_EQUAL, "<=", startLine, startColumn);
            return makeToken(TokenType::LESS, "<", startLine, startColumn);
        case '&':
            if (match('&')) return makeToken(TokenType::AND, "&&", startLine, startColumn);
            fail("Single '&' is not an operator; use '&&' or 'and'", startLine, startColumn);
        case '|':
            if (match('|')) return makeToken(TokenType::OR, "||", startLine, startColumn);
            fail("Single '|' is not an operator; use '||' or 'or'", startLine, startColumn);
        case '\\':
            if (!isAtEnd() && peek() == '\n') {
                advance(); 
                return lexSymbol();
            }
            fail("Stray backslash outside string; use it inside quotes", startLine, startColumn);
        default:
            break;
    }
    fail(std::string("Unexpected character '") + c + "'", startLine, startColumn);
}

std::vector<Token> Lexer::tokenize() {
    std::vector<Token> tokens;

    while (!isAtEnd()) {
        skipWhitespace();
        if (isAtEnd()) break;

        tokenStart_ = position_;
        char c = peek();
        if (c == '\n') {
            const std::size_t newlineLine = line_;
            const std::size_t newlineColumn = column_;
            advance();
            tokens.push_back(makeToken(TokenType::NEWLINE, "", newlineLine,
                                       newlineColumn));
            continue;
        }
        if (c == '#') {
            skipComment();
            continue;
        }
        if (c == '"' || c == '\'') {
            tokens.push_back(lexString());
            continue;
        }
        if (c == '$') {
            tokens.push_back(lexVariable());
            continue;
        }
        if (isDigit(c)) {
            tokens.push_back(lexNumber());
            continue;
        }
        if (isAlpha(c)) {
            tokens.push_back(lexIdentifierOrKeyword());
            continue;
        }

        if (c == '\\' && peekNext() == '\n') {
            advance();  // '\\'.
            advance();  // '\n'.
            continue;
        }
        tokens.push_back(lexSymbol());
    }

    tokenStart_ = position_;
    tokens.push_back(makeToken(TokenType::END_OF_FILE, "", line_, column_));
    return tokens;
}


#include <iostream>

#ifndef IOSTREAM_H
#define IOSTREAM_H


#endif  /*IOSTREAM_H*/