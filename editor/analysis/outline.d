module editor.analysis.outline;

import editor.analysis.types;
import editor.analysis.parser;

class OutlineBuilder {
    
    OutlineItem[] build(ProgramNode program) {
        OutlineItem[] items;
        if (program is null) return items;

        foreach (stmt; program.statements) {
            auto item = visitStatement(stmt);
            if (item.name.length > 0) {
                items ~= item;
            }
        }
        return items;
    }

    private OutlineItem visitStatement(StmtNode stmt) {
        OutlineItem item;

        if (auto fn = cast(FunctionDeclNode) stmt) {
            item.name = fn.name;
            item.kind = SymbolKind.Function;
            item.span = fn.span;
        } 
        else if (auto cls = cast(ClassDeclNode) stmt) {
            item.name = cls.name;
            item.kind = SymbolKind.Class;
            item.span = cls.span;

            foreach (member; cls.members) {
                auto child = visitStatement(member);
                if (child.name.length > 0) {
                    item.children ~= child;
                }
            }
        }
        else if (auto imp = cast(ImportNode) stmt) {
            item.name = imp.moduleName;
            item.kind = SymbolKind.Import;
            item.span = imp.span;
        }
        else if (auto var = cast(VarDeclNode) stmt) {
            item.name = var.varName;
            item.kind = SymbolKind.Variable;
            item.span = var.span;
        }

        return item;
    }
}