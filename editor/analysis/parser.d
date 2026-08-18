module editor.analysis.parser;

import editor.analysis.types;
import editor.analysis.lexer;
import std.format : format;

// --- AST Node Definitions ---

abstract class ASTNode {
    SourceSpan span;
    abstract string prettyPrint(int indent = 0) const;
}

abstract class ExprNode : ASTNode {}
abstract class StmtNode : ASTNode {}

class ImportNode : StmtNode {
    string moduleName;
    this(string moduleName, SourceSpan span) {
        this.moduleName = moduleName;
        this.span = span;
    }
    override string prettyPrint(int indent = 0) const {
        return format("%*sImportNode(%s)", indent * 2, "", moduleName);
    }
}

class VarDeclNode : StmtNode {
    string varName;
    ExprNode initializer;
    this(string varName, ExprNode initializer, SourceSpan span) {
        this.varName = varName;
        this.initializer = initializer;
        this.span = span;
    }
    override string prettyPrint(int indent = 0) const {
        string pad = format("%*s", indent * 2, "");
        if (initializer !is null) {
            return format("%sVarDecl(%s):\n%s", pad, varName, initializer.prettyPrint(indent + 1));
        }
        return format("%sVarDecl(%s)", pad, varName);
    }
}

class FunctionDeclNode : StmtNode {
    string name;
    string[] params;
    StmtNode[] bodyStatements;
    this(string name, string[] params, StmtNode[] bodyStatements, SourceSpan span) {
        this.name = name;
        this.params = params;
        this.bodyStatements = bodyStatements;
        this.span = span;
    }
    override string prettyPrint(int indent = 0) const {
        string pad = format("%*s", indent * 2, "");
        string result = format("%sFunctionDecl: %s(params: %s)\n", pad, name, params);
        foreach (stmt; bodyStatements) {
            if (stmt !is null) result ~= stmt.prettyPrint(indent + 1) ~ "\n";
        }
        return result;
    }
}

class ClassDeclNode : StmtNode {
    string name;
    StmtNode[] members;
    this(string name, StmtNode[] members, SourceSpan span) {
        this.name = name;
        this.members = members;
        this.span = span;
    }
    override string prettyPrint(int indent = 0) const {
        string pad = format("%*s", indent * 2, "");
        string result = format("%sClassDecl: %s\n", pad, name);
        foreach (m; members) {
            if (m !is null) result ~= m.prettyPrint(indent + 1) ~ "\n";
        }
        return result;
    }
}

class ReturnNode : StmtNode {
    ExprNode value;
    this(ExprNode value, SourceSpan span) {
        this.value = value;
        this.span = span;
    }
    override string prettyPrint(int indent = 0) const {
        string pad = format("%*s", indent * 2, "");
        if (value !is null) {
            return format("%sReturnStmt:\n%s", pad, value.prettyPrint(indent + 1));
        }
        return format("%sReturnStmt", pad);
    }
}

class LiteralNode : ExprNode {
    Token token;
    this(Token token) {
        this.token = token;
        this.span = token.span;
    }
    override string prettyPrint(int indent = 0) const {
        return format("%*sLiteral(%s)", indent * 2, "", token.value);
    }
}

class IdentifierNode : ExprNode {
    string name;
    this(Token token) {
        this.name = token.value;
        this.span = token.span;
    }
    override string prettyPrint(int indent = 0) const {
        return format("%*sIdentifier(%s)", indent * 2, "", name);
    }
}

class BinaryExprNode : ExprNode {
    ExprNode left;
    Token op;
    ExprNode right;
    this(ExprNode left, Token op, ExprNode right, SourceSpan span) {
        this.left = left;
        this.op = op;
        this.right = right;
        this.span = span;
    }
    override string prettyPrint(int indent = 0) const {
        string pad = format("%*s", indent * 2, "");
        return format("%sBinaryExpr(%s):\n%s\n%s", pad, op.value,
            left ? left.prettyPrint(indent + 1) : "null",
            right ? right.prettyPrint(indent + 1) : "null");
    }
}

class ProgramNode : ASTNode {
    StmtNode[] statements;
    override string prettyPrint(int indent = 0) const {
        string result = "Program:\n";
        foreach (stmt; statements) {
            if (stmt !is null) result ~= stmt.prettyPrint(indent + 1) ~ "\n";
        }
        return result;
    }
}

// --- Parser Implementation ---

struct Parser {
    private Token[] tokens;
    private size_t current = 0;
    Diagnostic[] diagnostics;

    this(Token[] tokens) {
        this.tokens = tokens;
    }

    ProgramNode parseProgram() {
        auto program = new ProgramNode();
        size_t startByte = tokens.length > 0 ? tokens[0].span.byteStart : 0;

        while (!isAtEnd()) {
            skipIgnoredTokens();
            if (isAtEnd()) break;

            try {
                auto stmt = parseStatement();
                if (stmt !is null) {
                    program.statements ~= stmt;
                }
            } catch (Exception e) {
                // Recover on statement boundary
                synchronize();
            }
        }

        size_t endByte = tokens.length > 0 ? tokens[$-1].span.byteEnd : 0;
        program.span = SourceSpan(1, 1, tokens.length > 0 ? tokens[$-1].span.lineEnd : 1, 1, startByte, endByte);
        return program;
    }

    private StmtNode parseStatement() {
        if (checkKeyword("import")) return parseImport();
        if (checkKeyword("class"))  return parseClass();
        if (checkKeyword("def") || checkKeyword("fn")) return parseFunction();
        if (checkKeyword("var") || checkKeyword("let")) return parseVarDecl();
        if (checkKeyword("return")) return parseReturn();

        return parseExpressionStatement();
    }

    private ImportNode parseImport() {
        Token startTok = consumeKeyword("import", "Expected 'import'");
        Token nameTok = consume(TokenType.Identifier, "Expected module name after 'import'");
        SourceSpan span = SourceSpan(startTok.span.lineStart, startTok.span.colStart, nameTok.span.lineEnd, nameTok.span.colEnd, startTok.span.byteStart, nameTok.span.byteEnd);
        return new ImportNode(nameTok.value, span);
    }

    private ClassDeclNode parseClass() {
        Token startTok = consumeKeyword("class", "Expected 'class'");
        Token nameTok = consume(TokenType.Identifier, "Expected class name");
        consumePunctuation("{", "Expected '{' before class body");

        StmtNode[] members;
        while (!checkPunctuation("}") && !isAtEnd()) {
            skipIgnoredTokens();
            if (checkPunctuation("}")) break;
            members ~= parseStatement();
        }

        Token endTok = consumePunctuation("}", "Expected '}' after class body");
        SourceSpan span = SourceSpan(startTok.span.lineStart, startTok.span.colStart, endTok.span.lineEnd, endTok.span.colEnd, startTok.span.byteStart, endTok.span.byteEnd);
        return new ClassDeclNode(nameTok.value, members, span);
    }

    private FunctionDeclNode parseFunction() {
        Token startTok = advance(); // def or fn
        Token nameTok = consume(TokenType.Identifier, "Expected function name");
        consumePunctuation("(", "Expected '(' after function name");

        string[] params;
        if (!checkPunctuation(")")) {
            do {
                skipIgnoredTokens();
                Token p = consume(TokenType.Identifier, "Expected parameter name");
                params ~= p.value;
                skipIgnoredTokens();
            } while (matchPunctuation(","));
        }
        consumePunctuation(")", "Expected ')' after parameters");

        StmtNode[] bodyStmts;
        Token endTok;

        if (matchOperator(":")) {
            // Inline/Python style function
            while (!isAtEnd() && !checkKeyword("def") && !checkKeyword("fn") && !checkKeyword("class")) {
                skipIgnoredTokens();
                if (isAtEnd() || checkKeyword("def") || checkKeyword("fn")) break;
                bodyStmts ~= parseStatement();
            }
            endTok = previous();
        } else if (matchPunctuation("{")) {
            // C/Rust style function block
            while (!checkPunctuation("}") && !isAtEnd()) {
                skipIgnoredTokens();
                if (checkPunctuation("}")) break;
                bodyStmts ~= parseStatement();
            }
            endTok = consumePunctuation("}", "Expected '}' after function body");
        } else {
            reportError("Expected ':' or '{' to start function body", peek().span);
            endTok = nameTok;
        }

        SourceSpan span = SourceSpan(startTok.span.lineStart, startTok.span.colStart, endTok.span.lineEnd, endTok.span.colEnd, startTok.span.byteStart, endTok.span.byteEnd);
        return new FunctionDeclNode(nameTok.value, params, bodyStmts, span);
    }

    private VarDeclNode parseVarDecl() {
        Token startTok = advance(); // var or let
        Token nameTok = consume(TokenType.Identifier, "Expected variable name");

        ExprNode initExpr = null;
        Token endTok = nameTok;

        if (matchOperator("=")) {
            initExpr = parseExpression();
            if (initExpr !is null) endTok = Token(TokenType.Unknown, "", initExpr.span);
        }

        matchPunctuation(";"); // optional semicolon

        SourceSpan span = SourceSpan(startTok.span.lineStart, startTok.span.colStart, endTok.span.lineEnd, endTok.span.colEnd, startTok.span.byteStart, endTok.span.byteEnd);
        return new VarDeclNode(nameTok.value, initExpr, span);
    }

    private ReturnNode parseReturn() {
        Token startTok = consumeKeyword("return", "Expected 'return'");
        ExprNode val = null;

        if (!checkPunctuation(";") && !checkPunctuation("}") && peek().span.lineStart == startTok.span.lineStart) {
            val = parseExpression();
        }

        matchPunctuation(";");
        SourceSpan span = val !is null ? SourceSpan(startTok.span.lineStart, startTok.span.colStart, val.span.lineEnd, val.span.colEnd, startTok.span.byteStart, val.span.byteEnd) : startTok.span;

        return new ReturnNode(val, span);
    }

    private StmtNode parseExpressionStatement() {
        ExprNode expr = parseExpression();
        matchPunctuation(";");
        return expr !is null ? cast(StmtNode) expr : null;
    }

    private ExprNode parseExpression() {
        ExprNode left = parsePrimary();

        while (matchType(TokenType.Operator)) {
            Token op = previous();
            ExprNode right = parsePrimary();
            SourceSpan span = SourceSpan(left.span.lineStart, left.span.colStart, right ? right.span.lineEnd : op.span.lineEnd, right ? right.span.colEnd : op.span.colEnd, left.span.byteStart, right ? right.span.byteEnd : op.span.byteEnd);
            left = new BinaryExprNode(left, op, right, span);
        }

        return left;
    }

    private ExprNode parsePrimary() {
        skipIgnoredTokens();

        if (matchType(TokenType.Number) || matchType(TokenType.StringLiteral)) {
            return new LiteralNode(previous());
        }

        if (matchType(TokenType.Identifier)) {
            return new IdentifierNode(previous());
        }

        reportError(format("Unexpected token '%s'", peek().value), peek().span);
        advance();
        return null;
    }

    // --- Panic Mode Error Recovery ---

    private void synchronize() {
        advance();
        while (!isAtEnd()) {
            if (previous().type == TokenType.Punctuation && previous().value == ";") return;

            if (peek().type == TokenType.Keyword) {
                switch (peek().value) {
                    case "class", "def", "fn", "var", "let", "import", "return":
                        return;
                    default:
                        break;
                }
            }
            advance();
        }
    }

    // --- Helper Operations ---

    private void skipIgnoredTokens() {
        while (!isAtEnd() && (peek().type == TokenType.Whitespace || peek().type == TokenType.Comment)) {
            advance();
        }
    }

    private bool checkKeyword(string kw) {
        skipIgnoredTokens();
        return !isAtEnd() && peek().type == TokenType.Keyword && peek().value == kw;
    }

    private bool checkPunctuation(string p) {
        skipIgnoredTokens();
        return !isAtEnd() && peek().type == TokenType.Punctuation && peek().value == p;
    }

    private bool matchOperator(string op) {
        skipIgnoredTokens();
        if (!isAtEnd() && peek().type == TokenType.Operator && peek().value == op) {
            advance();
            return true;
        }
        return false;
    }

    private bool matchPunctuation(string p) {
        if (checkPunctuation(p)) {
            advance();
            return true;
        }
        return false;
    }

    private bool matchType(TokenType type) {
        skipIgnoredTokens();
        if (!isAtEnd() && peek().type == type) {
            advance();
            return true;
        }
        return false;
    }

    private Token consume(TokenType type, string errorMsg) {
        skipIgnoredTokens();
        if (!isAtEnd() && peek().type == type) return advance();
        reportError(errorMsg, peek().span);
        throw new Exception(errorMsg);
    }

    private Token consumeKeyword(string kw, string errorMsg) {
        if (checkKeyword(kw)) return advance();
        reportError(errorMsg, peek().span);
        throw new Exception(errorMsg);
    }

    private Token consumePunctuation(string p, string errorMsg) {
        if (checkPunctuation(p)) return advance();
        reportError(errorMsg, peek().span);
        throw new Exception(errorMsg);
    }

    private void reportError(string msg, SourceSpan span) {
        diagnostics ~= Diagnostic(DiagnosticCategory.GrammarError, msg, "", span);
    }

    private Token advance() {
        if (!isAtEnd()) current++;
        return previous();
    }

    private bool isAtEnd() const { return current >= tokens.length || tokens[current].type == TokenType.EOF; }
    private Token peek() const { return tokens[current]; }
    private Token previous() const { return tokens[current - 1]; }
}