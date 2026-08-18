module editor.analysis.lexer;

import editor.analysis.types;
import std.ascii : isWhite, isAlpha, isAlphaNum, isDigit;

enum TokenType {
    Identifier,
    Keyword,
    Number,
    StringLiteral,
    Operator,
    Punctuation,
    Comment,
    Whitespace,
    Unknown,
    EOF
}

struct Token {
    TokenType type;
    string value;
    SourceSpan span;
}

struct Lexer {
    private string source;
    private size_t cursor = 0;
    private size_t line = 1;
    private size_t col = 1;

    this(string source) {
        this.source = source;
    }

    Token[] tokenize() {
        Token[] tokens;
        while (cursor < source.length) {
            tokens ~= nextToken();
        }
        SourceSpan eofSpan = SourceSpan(line, col, line, col, cursor, cursor);
        tokens ~= Token(TokenType.EOF, "", eofSpan);
        return tokens;
    }

    Token nextToken() {
        if (cursor >= source.length) {
            SourceSpan eofSpan = SourceSpan(line, col, line, col, cursor, cursor);
            return Token(TokenType.EOF, "", eofSpan);
        }

        size_t startByte = cursor;
        size_t startLine = line;
        size_t startCol = col;

        char ch = source[cursor];

        if (isWhite(ch)) {
            while (cursor < source.length && isWhite(source[cursor])) {
                advance();
            }
            SourceSpan span = SourceSpan(startLine, startCol, line, col, startByte, cursor);
            return Token(TokenType.Whitespace, source[startByte .. cursor], span);
        }

        if (ch == '#' || (ch == '/' && peek() == '/') || (ch == '/' && peek() == '*')) {
            return lexComment(startLine, startCol, startByte);
        }

        if (isAlpha(ch) || ch == '_') {
            while (cursor < source.length && (isAlphaNum(source[cursor]) || source[cursor] == '_')) {
                advance();
            }
            string word = source[startByte .. cursor];
            TokenType type = isKeyword(word) ? TokenType.Keyword : TokenType.Identifier;
            SourceSpan span = SourceSpan(startLine, startCol, line, col, startByte, cursor);
            return Token(type, word, span);
        }

        if (isDigit(ch)) {
            while (cursor < source.length && (isDigit(source[cursor]) || source[cursor] == '.')) {
                advance();
            }
            SourceSpan span = SourceSpan(startLine, startCol, line, col, startByte, cursor);
            return Token(TokenType.Number, source[startByte .. cursor], span);
        }

        if (ch == '"' || ch == '\'') {
            return lexString(ch, startLine, startCol, startByte);
        }

        if (isOperatorChar(ch)) {
            advance();
            if (cursor < source.length && isOperatorChar(source[cursor])) {
                advance();
            }
            SourceSpan span = SourceSpan(startLine, startCol, line, col, startByte, cursor);
            return Token(TokenType.Operator, source[startByte .. cursor], span);
        }

        if (isPunctuationChar(ch)) {
            advance();
            SourceSpan span = SourceSpan(startLine, startCol, line, col, startByte, cursor);
            return Token(TokenType.Punctuation, source[startByte .. cursor], span);
        }

        advance();
        SourceSpan span = SourceSpan(startLine, startCol, line, col, startByte, cursor);
        return Token(TokenType.Unknown, source[startByte .. cursor], span);
    }

    private void advance() {
        if (cursor < source.length) {
            if (source[cursor] == '\n') {
                line++;
                col = 1;
            } else {
                col++;
            }
            cursor++;
        }
    }

    private char peek() const {
        if (cursor + 1 < source.length) return source[cursor + 1];
        return '\0';
    }

    private bool isKeyword(string word) const {
        switch (word) {
            case "import", "class", "def", "fn", "var", "let", "return", "if", "else", "while":
                return true;
            default:
                return false;
        }
    }

    private Token lexString(char quote, size_t startLine, size_t startCol, size_t startByte) {
        advance();
        while (cursor < source.length) {
            if (source[cursor] == '\\' && cursor + 1 < source.length) {
                advance();
                advance();
                continue;
            }
            if (source[cursor] == quote) {
                advance();
                break;
            }
            advance();
        }
        SourceSpan span = SourceSpan(startLine, startCol, line, col, startByte, cursor);
        return Token(TokenType.StringLiteral, source[startByte .. cursor], span);
    }

    private Token lexComment(size_t startLine, size_t startCol, size_t startByte) {
        if (source[cursor] == '#' || (source[cursor] == '/' && peek() == '/')) {
            while (cursor < source.length && source[cursor] != '\n') advance();
        } else if (source[cursor] == '/' && peek() == '*') {
            advance(); advance();
            while (cursor + 1 < source.length && !(source[cursor] == '*' && source[cursor + 1] == '/')) {
                advance();
            }
            if (cursor + 1 < source.length) { advance(); advance(); }
        }
        SourceSpan span = SourceSpan(startLine, startCol, line, col, startByte, cursor);
        return Token(TokenType.Comment, source[startByte .. cursor], span);
    }

    private bool isOperatorChar(char c) const {
        import std.algorithm.searching : canFind;
        return "+-*/%=<>&|^!~:?".canFind(c);
    }

    private bool isPunctuationChar(char c) const {
        import std.algorithm.searching : canFind;
        return "(){}[];,.".canFind(c);
    }
}