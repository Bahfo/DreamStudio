#include "parser.hpp"

#include <memory>
#include <stdexcept>
#include <utility>

Parser::Parser(const std::vector<Token>& tokens) : tokens(tokens) {}

const Token& Parser::peek() const {
    return tokens[current_];
}

const Token& Parser::advance() {
    if (!isAtEnd()) {
        ++current_;
    }
    return tokens[current_];
}

bool Parser::isAtEnd() const {
    return peek().type == TokenType::END_OF_FILE;
}

bool Parser::check(TokenType type) const {
    if (isAtEnd()) {
        return false;
    }
    return peek().type == type;
}

bool Parser::checkNext(TokenType type) const {
    if (current_ + 1 >= tokens.size()) {
        return false;
    }
    return tokens[current_ + 1].type == type;
}

bool Parser::match(TokenType type) {
    if (!check(type)) {
        return false;
    }
    advance();
    return true;
}

const Token& Parser::consume(TokenType type, const std::string& message) {
    if (check(type)) {
        return advance();
    }
    fail(message);
}

void Parser::fail(const std::string& message) const {
    const Token& token = peek();
    throw std::runtime_error(
        message + " at line " + std::to_string(token.line) +
        ", column " + std::to_string(token.column) + ".");
}

void Parser::skipSeparators() {
    while (match(TokenType::NEWLINE) || match(TokenType::SEMICOLON)) {
    }
}

void Parser::skipNewlines() {
    while (match(TokenType::NEWLINE)) {
    }
}

bool Parser::nextIsAfterNewlines(TokenType type) const {
    std::size_t offset = 1;
    while (current_ + offset < tokens.size() &&
           tokens[current_ + offset].type == TokenType::NEWLINE) {
        ++offset;
    }
    return current_ + offset < tokens.size() &&
           tokens[current_ + offset].type == type;
}

StatementPtr Parser::parseStatement() {
    if (check(TokenType::IF)) {
        return parseIf();
    }
    if (check(TokenType::WHILE)) {
        return parseWhile();
    }
    if (check(TokenType::LEFT_BRACE)) {
        return parseBlock();
    }
    if (check(TokenType::VARIABLE) && checkNext(TokenType::ASSIGN)) {
        return parseAssignment();
    }
    return parseCommand();
}

StatementPtr Parser::parseAssignment() {
    Token target = consume(TokenType::VARIABLE, "Expected variable name");
    consume(TokenType::ASSIGN, "Expected '=' after variable name");
    ExpressionPtr value = parseExpression();

    auto statement = std::make_unique<AssignStatement>();
    statement->target = target;
    statement->value = std::move(value);
    return statement;
}

StatementPtr Parser::parseCommand() {
    Token name = advance();

    auto statement = std::make_unique<CommandStatement>();
    statement->name = name;

    while (!check(TokenType::NEWLINE) && !check(TokenType::SEMICOLON) &&
           !check(TokenType::RIGHT_BRACE) && !check(TokenType::RIGHT_PAREN) &&
           !isAtEnd()) {
        if (check(TokenType::COMMA)) {
            advance();
            continue;
        }
        statement->arguments.push_back(advance());
    }
    return statement;
}

std::unique_ptr<BlockStatement> Parser::parseBlock() {
    Token openingBrace = consume(TokenType::LEFT_BRACE, "Expected '{'");

    auto block = std::make_unique<BlockStatement>();
    block->openingBrace = openingBrace;

    skipSeparators();
    while (!check(TokenType::RIGHT_BRACE) && !isAtEnd()) {
        block->statements.push_back(parseStatement());
        skipSeparators();
    }
    consume(TokenType::RIGHT_BRACE, "Expected '}'");
    return block;
}

StatementPtr Parser::parseIf() {
    Token keyword = consume(TokenType::IF, "Expected 'if'");
    ExpressionPtr condition = parseExpression();
    consume(TokenType::THEN, "Expected 'then' after if condition");
    auto thenBranch = parseBlock();

    std::unique_ptr<BlockStatement> elseBranch;
    if (match(TokenType::ELSE)) {
        elseBranch = parseBlock();
    }

    auto statement = std::make_unique<IfStmt>();
    statement->keyword = keyword;
    statement->condition = std::move(condition);
    statement->thenBranch = std::move(thenBranch);
    statement->elseBranch = std::move(elseBranch);
    return statement;
}

StatementPtr Parser::parseWhile() {
    Token keyword = consume(TokenType::WHILE, "Expected 'while'");
    ExpressionPtr condition = parseExpression();
    consume(TokenType::THEN, "Expected 'then' after while condition");
    auto body = parseBlock();

    auto statement = std::make_unique<WhileStmt>();
    statement->keyword = keyword;
    statement->condition = std::move(condition);
    statement->body = std::move(body);
    return statement;
}

ExpressionPtr Parser::parseExpression() {
    return parseOr();
}

ExpressionPtr Parser::parseOr() {
    ExpressionPtr expr = parseAnd();
    while (check(TokenType::OR)) {
        Token op = advance();
        ExpressionPtr right = parseAnd();

        auto binary = std::make_unique<BinaryExpression>();
        binary->left = std::move(expr);
        binary->operand = op;
        binary->right = std::move(right);
        expr = std::move(binary);
    }
    return expr;
}

ExpressionPtr Parser::parseAnd() {
    ExpressionPtr expr = parseEquality();
    while (check(TokenType::AND)) {
        Token op = advance();
        ExpressionPtr right = parseEquality();

        auto binary = std::make_unique<BinaryExpression>();
        binary->left = std::move(expr);
        binary->operand = op;
        binary->right = std::move(right);
        expr = std::move(binary);
    }
    return expr;
}

ExpressionPtr Parser::parseEquality() {
    ExpressionPtr expr = parseComparison();
    while (check(TokenType::EQUAL_EQUAL) || check(TokenType::BANG_EQUAL)) {
        Token op = advance();
        ExpressionPtr right = parseComparison();

        auto binary = std::make_unique<BinaryExpression>();
        binary->left = std::move(expr);
        binary->operand = op;
        binary->right = std::move(right);
        expr = std::move(binary);
    }
    return expr;
}

ExpressionPtr Parser::parseComparison() {
    ExpressionPtr expr = parseTerm();
    while (check(TokenType::GREATER) || check(TokenType::GREATER_EQUAL) ||
           check(TokenType::LESS) || check(TokenType::LESS_EQUAL)) {
        Token op = advance();
        ExpressionPtr right = parseTerm();

        auto binary = std::make_unique<BinaryExpression>();
        binary->left = std::move(expr);
        binary->operand = op;
        binary->right = std::move(right);
        expr = std::move(binary);
    }
    return expr;
}

ExpressionPtr Parser::parseTerm() {
    ExpressionPtr expr = parseFactor();
    while (check(TokenType::PLUS) || check(TokenType::MINUS)) {
        Token op = advance();
        ExpressionPtr right = parseFactor();

        auto binary = std::make_unique<BinaryExpression>();
        binary->left = std::move(expr);
        binary->operand = op;
        binary->right = std::move(right);
        expr = std::move(binary);
    }
    return expr;
}

ExpressionPtr Parser::parseFactor() {
    ExpressionPtr expr = parseUnary();
    while (check(TokenType::STAR) || check(TokenType::SLASH) ||
           check(TokenType::PERCENT)) {
        Token op = advance();
        ExpressionPtr right = parseUnary();

        auto binary = std::make_unique<BinaryExpression>();
        binary->left = std::move(expr);
        binary->operand = op;
        binary->right = std::move(right);
        expr = std::move(binary);
    }
    return expr;
}

ExpressionPtr Parser::parseUnary() {
    if (check(TokenType::NOT)) {
        Token op = advance();
        ExpressionPtr operand = parseUnary();

        auto unary = std::make_unique<UnaryExpression>();
        unary->op = op;
        unary->operand = std::move(operand);
        return unary;
    }
    return parsePrimary();
}

ExpressionPtr Parser::parsePrimary() {
    if (check(TokenType::NUMBER) || check(TokenType::STRING) ||
        check(TokenType::TRUE) || check(TokenType::FALSE) ||
        check(TokenType::VARIABLE) || check(TokenType::ENV_VARIABLE)) {
        Token token = advance();

        auto literal = std::make_unique<LiteralExpression>();
        literal->token = token;
        return literal;
    }
    if (check(TokenType::LEFT_PAREN)) {
        advance();
        ExpressionPtr expr = parseExpression();
        consume(TokenType::RIGHT_PAREN, "Expected ')' after expression");
        return expr;
    }
    fail("Expected expression");
}

Program Parser::parse() {
    Program program;

    skipSeparators();
    while (!isAtEnd()) {
        program.statements.push_back(parseStatement());
        skipSeparators();
    }
    return program;
}
