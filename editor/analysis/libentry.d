module editor.analysis.libentry;

import core.runtime;
import std.string : toStringz, fromStringz;
import std.json;

import editor.analysis.types;
import editor.analysis.lexer;
import editor.analysis.parser;
import editor.analysis.resolver;
import editor.analysis.diagnostics;
import editor.analysis.outline;


version (Windows) {
    import core.sys.windows.windows;
    extern (Windows) BOOL DllMain(HINSTANCE hInstance, ULONG ulReason, LPVOID pvReserved) {
        switch (ulReason) {
            case DLL_PROCESS_ATTACH:
                Runtime.initialize();
                break;
            case DLL_PROCESS_DETACH:
                Runtime.terminate();
                break;
            default:
                break;
        }
        return TRUE;
    }
} else version (Posix) {
    import core.sys.posix.dlfcn;

    shared static this() {
        Runtime.initialize();
    }

    shared static ~this() {
        Runtime.terminate();
    }
}

extern (C) {

    export char* analyze_code(const char* cSource) {
        if (cSource is null) return cast(char*) toStringz("{}");

        string source = cast(string) fromStringz(cSource);

        auto lexer = Lexer(source);
        auto tokens = lexer.tokenize();

        auto parser = Parser(tokens);
        auto ast = parser.parseProgram();
        Diagnostic[] diagnostics = parser.diagnostics;

        auto resolver = new ScopeResolver();
        resolver.resolve(ast);
        diagnostics ~= resolver.diagnostics;

        auto diagEngine = new DiagnosticEngine();
        diagEngine.enrichTypoSuggestions(diagnostics, resolver.globalScope);
        diagEngine.detectSilentCode(ast, diagnostics);

        auto outlineBuilder = new OutlineBuilder();
        OutlineItem[] outline = outlineBuilder.build(ast);

        JSONValue root = JSONValue([
            "diagnostics": JSONValue(serializeDiagnostics(diagnostics)),
            "outline": JSONValue(serializeOutline(outline))
        ]);

        string jsonStr = root.toString();

        import core.stdc.stdlib : malloc;
        import core.stdc.string : memcpy;

        char* result = cast(char*) malloc(jsonStr.length + 1);
        memcpy(result, jsonStr.ptr, jsonStr.length);
        result[jsonStr.length] = '\0';

        return result;
    }

    export void free_result(char* ptr) {
        import core.stdc.stdlib : free;
        if (ptr !is null) {
            free(ptr);
        }
    }
}

private JSONValue[] serializeDiagnostics(Diagnostic[] diagnostics) {
    JSONValue[] arr;
    foreach (d; diagnostics) {
        JSONValue item = JSONValue([
            "category": JSONValue(cast(int) d.category),
            "message": JSONValue(d.message),
            "suggestion": JSONValue(d.suggestion),
            "span": JSONValue([
                "lineStart": JSONValue(d.span.lineStart),
                "colStart": JSONValue(d.span.colStart),
                "lineEnd": JSONValue(d.span.lineEnd),
                "colEnd": JSONValue(d.span.colEnd),
                "byteStart": JSONValue(d.span.byteStart),
                "byteEnd": JSONValue(d.span.byteEnd)
            ])
        ]);
        arr ~= item;
    }
    return arr;
}

private JSONValue[] serializeOutline(OutlineItem[] items) {
    JSONValue[] arr;
    foreach (item; items) {
        JSONValue node = JSONValue([
            "name": JSONValue(item.name),
            "kind": JSONValue(cast(int) item.kind),
            "span": JSONValue([
                "lineStart": JSONValue(item.span.lineStart),
                "colStart": JSONValue(item.span.colStart),
                "lineEnd": JSONValue(item.span.lineEnd),
                "colEnd": JSONValue(item.span.colEnd)
            ]),
            "children": JSONValue(serializeOutline(item.children))
        ]);
        arr ~= node;
    }
    return arr;
}