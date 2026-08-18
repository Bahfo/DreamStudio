module editor.analysis.diagnostics;

import editor.analysis.types;
import editor.analysis.parser;
import std.algorithm : min;
import std.format : format;
import std.math : abs;

size_t levenshteinDistance(string s1, string s2) {
    size_t m = s1.length;
    size_t n = s2.length;
    
    auto dp = new size_t[][](m + 1, n + 1);
    foreach (i; 0 .. m + 1) dp[i][0] = i;
    foreach (j; 0 .. n + 1) dp[0][j] = j;

    foreach (i; 1 .. m + 1) {
        foreach (j; 1 .. n + 1) {
            if (s1[i - 1] == s2[j - 1]) {
                dp[i][j] = dp[i - 1][j - 1];
            } else {
                dp[i][j] = 1 + min(dp[i - 1][j],      // Deletion
                                  dp[i][j - 1],       // Insertion
                                  dp[i - 1][j - 1]);  // Substitution
            }
        }
    }
    return dp[m][n];
}

class DiagnosticEngine {

    void enrichTypoSuggestions(ref Diagnostic[] diagnostics, Scope globalScope) {
        foreach (ref diag; diagnostics) {
            if (diag.category == DiagnosticCategory.GeneralError) {
                string unkName;
                if (formattedRead(diag.message, "Undefined identifier '%s'", unkName)) {
                    string bestMatch = findClosestMatch(unkName, globalScope);
                    if (bestMatch.length > 0) {
                        diag.category = DiagnosticCategory.TypoWarning;
                        diag.suggestion = bestMatch;
                        diag.message = format("Undefined identifier '%s'. Did you mean '%s'?", unkName, bestMatch);
                    }
                }
            }
        }
    }

    void detectSilentCode(ProgramNode program, ref Diagnostic[] diagnostics) {
        if (program is null) return;
        foreach (stmt; program.statements) {
            if (auto fn = cast(FunctionDeclNode) stmt) {
                checkBlockForSilentCode(fn.bodyStatements, diagnostics);
            }
        }
    }

    private string findClosestMatch(string target, Scope currentScope) {
        string bestMatch = "";
        size_t minDistance = size_t.max;

        Scope scopePtr = currentScope;
        while (scopePtr !is null) {
            foreach (name, sym; scopePtr.symbols) {
                if (abs(cast(long)name.length - cast(long)target.length) > 3) continue;
                
                size_t dist = levenshteinDistance(target, name);
                if (dist <= 2 && dist < minDistance) {
                    minDistance = dist;
                    bestMatch = name;
                }
            }
            scopePtr = scopePtr.parent;
        }
        return bestMatch;
    }

    private void checkBlockForSilentCode(StmtNode[] statements, ref Diagnostic[] diagnostics) {
        bool unreachable = false;

        foreach (stmt; statements) {
            if (stmt is null) continue;

            if (unreachable) {
                diagnostics ~= Diagnostic(
                    DiagnosticCategory.SilentCodeWarning,
                    "Silent/Unreachable code detected: statement will never execute",
                    "remove",
                    stmt.span
                );
            }

            if (cast(ReturnNode) stmt) {
                unreachable = true;
            }
        }
    }
}

import std.format : formattedRead;