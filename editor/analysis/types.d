module editor.analysis.types;

import std.format : format;

struct SourceSpan {
    size_t lineStart; 
    size_t colStart;
    size_t lineEnd;
    size_t colEnd;
    size_t byteStart;
    size_t byteEnd;

    string toString() const{
        return format("%d:%d - %d:%d", lineStart, colStart, lineEnd, colEnd);
    }
}

enum SymbolKind {
    Module,
    Import,
    Class,
    Function,
    Variable,
    Parameter,
}

class Symbol {
    string name;
    SymbolKind symbol;
    SourceSpan span;
    size_t useCount = 0;
    Scope enclosingScope;

    this(string name, SymbolKind symbol, SourceSpan span) {
        this.name = name;
        this.symbol = symbol;
        this.span = span;
    }
}

class Scope {
    size_t id;
    Scope parent;
    Scope[] children;
    Symbol[string] symbols;

    this(size_t id, Scope parent = null) {
        this.id = id;
        this.parent = parent;
        if (parent !is null) {
            parent.children ~= this;
        }
    }

    void insert(Symbol sym) {
        sym.enclosingScope = this;
        symbols[sym.name] = sym;
    }
    
    Symbol lookup(string name) {
        if (auto p = name in symbols) return *p;
        if (parent !is null) return parent.lookup(name);
        return null;
    }
}

enum DiagnosticCategory {
    GrammarError,       // Syntax errors
    GeneralError,       // Type / semantic failures
    TypoWarning,        // Misspelled identifiers or stylistic mismatches
    UnusedWarning,      // Unused imports, variables, functions, classes
    SilentCodeWarning   // Unreachable/dead code blocks, unused expressions
}

struct Diagnostic {
    DiagnosticCategory category;
    string message;
    string suggestion;
    SourceSpan span;
}

struct OutlineItem {
    string name;
    SymbolKind kind;
    SourceSpan span;
    OutlineItem[] children;
}