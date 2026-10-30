#pragma once

#include <cstddef>
#include <string>

enum class TokenType {
    END_OF_FILE,
    NEWLINE,
    STRING,
    NUMBER,
    IDENTIFIER,
    VARIABLE,
    ENV_VARIABLE,
    PRINT,
    INPUT,
    LIST_ITEMS,
    CHANGE_DIRECTORY,
    IF,
    THEN,
    ELSE,
    WHILE,
    TRUE,
    FALSE,
    AND,
    OR,
    NOT,
    ASSIGN,
    EQUAL_EQUAL,
    BANG_EQUAL,
    GREATER,        
    GREATER_EQUAL,
    LESS,           
    LESS_EQUAL,
    PLUS,           
    MINUS,          
    STAR,           
    SLASH,          
    PERCENT,        
    LEFT_PAREN,     
    RIGHT_PAREN,    
    LEFT_BRACE,     
    RIGHT_BRACE,    
    COMMA,          
    SEMICOLON,      
    COLON,          
    DOT,            
};

struct Token {
    TokenType type;
    std::string value;

    std::size_t line;
    std::size_t column;

    // Exact source spelling, including quotes and punctuation. The parser
    // uses this to rebuild shell-style command words.
    std::string lexeme;
};

std::string tokenTypeToString(TokenType type);
