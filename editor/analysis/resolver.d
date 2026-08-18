module editor.analysis.resolver;

import editor.analysis.types;
import editor.analysis.parser;
import std.format : format;

class ScopeResolver {
    Scope globalScope;
    Scope currentScope;
    Symbol[] allSymbols;
    Diagnostic[] diagnostics;
    private size_t scopeCounter = 0;

    this() {
        globalScope = new Scope(scopeCounter++);
        currentScope = globalScope;
    }

    void resolve(ProgramNode program) {
        if (program is null) return;

        foreach (stmt; program.statements) {
            visitStatement(stmt);
        }

        checkUnusedSymbols();
    }

    private void enterScope() {
        auto newScope = new Scope(scopeCounter++, currentScope);
        currentScope = newScope;
    }

    private void exitScope() {
        if (currentScope.parent !is null) {
            currentScope = currentScope.parent;
        }
    }

    private void declareSymbol(string name, SymbolKind kind, SourceSpan span) {
        if (auto existing = name in currentScope.symbols) {
            diagnostics ~= Diagnostic(
                DiagnosticCategory.GeneralError,
                format("Redeclaration of identifier '%s' in current scope", name),
                "",
                span
            );
            return;
        }

        auto sym = new Symbol(name, kind, span);
        currentScope.insert(sym);
        allSymbols ~= sym;
    }

    private void referenceSymbol(string name, SourceSpan span) {
        auto sym = currentScope.lookup(name);
        if (sym !is null) {
            sym.useCount++;
        } else {
            diagnostics ~= Diagnostic(
                DiagnosticCategory.GeneralError,
                format("Undefined identifier '%s'", name),
                "",
                span
            );
        }
    }

    private void visitStatement(StmtNode stmt) {
        if (stmt is null) return;

        if (auto imp = cast(ImportNode) stmt) {
            declareSymbol(imp.moduleName, SymbolKind.Import, imp.span);
        }
        else if (auto var = cast(VarDeclNode) stmt) {
            if (var.initializer !is null) {
                visitExpression(var.initializer);
            }
            declareSymbol(var.varName, SymbolKind.Variable, var.span);
        }
        else if (auto fn = cast(FunctionDeclNode) stmt) {
            declareSymbol(fn.name, SymbolKind.Function, fn.span);

            enterScope();
            foreach (param; fn.params) {
                declareSymbol(param, SymbolKind.Parameter, fn.span);
            }

            foreach (bodyStmt; fn.bodyStatements) {
                visitStatement(bodyStmt);
            }
            exitScope();
        }
        else if (auto cls = cast(ClassDeclNode) stmt) {
            declareSymbol(cls.name, SymbolKind.Class, cls.span);

            enterScope();
            foreach (member; cls.members) {
                visitStatement(member);
            }
            exitScope();
        }
        else if (auto ret = cast(ReturnNode) stmt) {
            if (ret.value !is null) {
                visitExpression(ret.value);
            }
        }
        else if (auto expr = cast(ExprNode) stmt) {
            visitExpression(expr);
        }
    }

    private void visitExpression(ExprNode expr) {
        if (expr is null) return;

        if (auto id = cast(IdentifierNode) expr) {
            referenceSymbol(id.name, id.span);
        }
        else if (auto bin = cast(BinaryExprNode) expr) {
            visitExpression(bin.left);
            visitExpression(bin.right);
        }
    }

    private void checkUnusedSymbols() {
        foreach (sym; allSymbols) {
            if (sym.useCount == 0) {
                string kindLabel;
                switch (sym.symbol) {
                    case SymbolKind.Import:    kindLabel = "import"; break;
                    case SymbolKind.Variable:  kindLabel = "variable"; break;
                    case SymbolKind.Function:  kindLabel = "function"; break;
                    case SymbolKind.Class:     kindLabel = "class"; break;
                    case SymbolKind.Parameter: kindLabel = "parameter"; break;
                    default:                   kindLabel = "symbol"; break;
                }

                diagnostics ~= Diagnostic(
                    DiagnosticCategory.UnusedWarning,
                    format("Unused %s '%s'", kindLabel, sym.name),
                    "remove",
                    sym.span
                );
            }
        }
    }
}