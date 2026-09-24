"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Libclang integration adapter for DreamStudio embedded C support.
"""

import logging
import os
import re
import clang.cindex

from typing import List, Optional
from clang.cindex import CursorKind, Index, TranslationUnit, Cursor

# Local Imports
from editor.Ironica.plugins.clang.clang_domain_models import *
from editor.Ironica.plugins.clang.c_interfaces import *

logger = logging.getLogger("DreamStudio.CSupport.ClangAdapter")


def _cursor_value(name: str) -> int:
    """Return the numeric libclang value for a cursor-kind name."""
    cursor_kind = getattr(CursorKind, name, None)
    return int(cursor_kind.value) if cursor_kind is not None else -1


_COMPLETION_KIND_MAP = {
    _cursor_value("FUNCTION_DECL"): "function",
    _cursor_value("CXX_METHOD"): "method",
    _cursor_value("CONSTRUCTOR"): "method",
    _cursor_value("DESTRUCTOR"): "method",
    _cursor_value("FUNCTION_TEMPLATE"): "function",
    _cursor_value("MACRO_DEFINITION"): "macro",
    _cursor_value("MACRO_INSTANTIATION"): "macro",
    _cursor_value("VAR_DECL"): "variable",
    _cursor_value("PARM_DECL"): "parameter",
    _cursor_value("FIELD_DECL"): "field",
    _cursor_value("ENUM_CONSTANT_DECL"): "constant",
    _cursor_value("ENUM_DECL"): "enum",
    _cursor_value("STRUCT_DECL"): "type",
    _cursor_value("UNION_DECL"): "type",
    _cursor_value("CLASS_DECL"): "type",
    _cursor_value("TYPEDEF_DECL"): "type",
    _cursor_value("TYPE_ALIAS_DECL"): "type",
    _cursor_value("NAMESPACE"): "namespace",
    _cursor_value("INCLUSION_DIRECTIVE"): "import",
    _cursor_value("MODULE_IMPORT_DECL"): "import",
    _cursor_value("PREPROCESSING_DIRECTIVE"): "preprocessor",
    _cursor_value("UNEXPOSED_DECL"): "builtin",
    _cursor_value("TYPE_REF"): "type",
    _cursor_value("NAMESPACE_REF"): "namespace",
}


class ClangAdapter(IClangAdapter):
    """Stateless adapter interfacing with libclang."""

    def __init__(self, library_path: Optional[str] = None) -> None:
        super().__init__()
        if library_path:
            clang.cindex.Config.set_library_file(library_path)
        self._index = Index.create()

    def _parse_translation_unit(self, context: CContext) -> Optional[TranslationUnit]:
        file_path = context.file_path or "unsaved_buffer.c"
        unsaved_files = [(file_path, context.source_code)]
        args = ["-x", "c", "-std=c11"] + context.compile_args

        try:
            return self._index.parse(
                path=file_path,
                args=args,
                unsaved_files=unsaved_files,
                options=(
                    TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
                    | TranslationUnit.PARSE_INCLUDE_BRIEF_COMMENTS_IN_CODE_COMPLETION
                    | TranslationUnit.PARSE_INCOMPLETE
                ),
            )
        except Exception as e:
            logger.error(
                "Failed to parse Clang TranslationUnit: %s", str(e), exc_info=True
            )
            return None

    @staticmethod
    def _resolve_hover_cursor(cursor: Cursor) -> Cursor:
        """Resolve expression and macro cursors to their declared symbol."""
        reference_kinds = {
            CursorKind.CALL_EXPR,
            CursorKind.MEMBER_REF_EXPR,
            CursorKind.DECL_REF_EXPR,
            CursorKind.MACRO_INSTANTIATION,
            CursorKind.TYPE_REF,
        }
        current = cursor
        for _ in range(4):
            if current.kind not in reference_kinds:
                break
            try:
                referenced = current.referenced
            except Exception:
                referenced = None
            if referenced is None or referenced == current:
                break
            current = referenced
        return current

    def get_hover(self, context: CContext) -> Optional[HoverDetails]:
        tu = self._parse_translation_unit(context)
        if not tu:
            return None

        file_path = context.file_path or "unsaved_buffer.c"
        target_file = tu.get_file(file_path)
        if not target_file:
            return None

        location = tu.get_location(file_path, (context.line, context.col))
        cursor = Cursor.from_location(tu, location)
        if not cursor or cursor.kind == CursorKind.TRANSLATION_UNIT:
            return None

        cursor = self._resolve_hover_cursor(cursor)
        params: List[ParameterInfo] = []
        return_type = None
        signature = cursor.displayname or cursor.spelling

        if cursor.kind in (CursorKind.FUNCTION_DECL, CursorKind.CXX_METHOD):
            return_type = cursor.result_type.spelling
            arguments = list(cursor.get_arguments())
            param_list = [
                f"{argument.type.spelling} {argument.spelling}".strip()
                for argument in arguments
            ]
            signature = f"{return_type} {cursor.spelling}({', '.join(param_list)})"
            for argument in arguments:
                params.append(
                    ParameterInfo(
                        name=argument.spelling or "param",
                        type_str=argument.type.spelling,
                    )
                )
        elif cursor.kind in (
            CursorKind.VAR_DECL,
            CursorKind.PARM_DECL,
            CursorKind.FIELD_DECL,
        ):
            signature = f"{cursor.type.spelling} {cursor.spelling}"
        elif cursor.kind in (
            CursorKind.MACRO_DEFINITION,
            CursorKind.MACRO_INSTANTIATION,
        ):
            signature = f"#define {cursor.spelling}"
        elif cursor.kind in (
            CursorKind.STRUCT_DECL,
            CursorKind.UNION_DECL,
            CursorKind.ENUM_DECL,
            CursorKind.CLASS_DECL,
        ):
            signature = f"{cursor.spelling}"

        raw_doc = cursor.raw_comment or cursor.brief_comment
        name = cursor.spelling or cursor.displayname or "symbol"
        return HoverDetails(
            name=name,
            kind=str(cursor.kind.name),
            signature=signature,
            parameters=params,
            return_type=return_type,
            docstring=raw_doc,
        )

    @staticmethod
    def _completion_kind(raw_kind: int) -> str:
        return _COMPLETION_KIND_MAP.get(raw_kind, "text")

    def _fallback_include_definition(
        self, context: CContext
    ) -> Optional[DefinitionLocation]:
        """Resolve header file path manually if libclang cannot locate it."""
        if not context.source_code:
            return None

        lines = context.source_code.splitlines()
        if context.line <= 0 or context.line > len(lines):
            return None

        line_text = lines[context.line - 1]
        match = re.match(r'^\s*#\s*include\s+[<"]([^>"]+)[>"]', line_text)
        if not match:
            return None

        header_name = match.group(1)
        base_dir = os.path.dirname(context.file_path) if context.file_path else ""

        if base_dir:
            rel_path = os.path.join(base_dir, header_name)
            if os.path.isfile(rel_path):
                return DefinitionLocation(
                    file_path=os.path.abspath(rel_path), line=1, column=1
                )

        search_dirs = [
            "/usr/include",
            "/usr/local/include",
            "/usr/include/x86_64-linux-gnu",
            "C:/msys64/mingw64/include",
            "C:/Program Files/LLVM/include",
            "C:/Program Files/LLVM/lib/clang/18/include",
            "C:/Program Files/LLVM/lib/clang/17/include",
            "C:/Program Files/LLVM/lib/clang/16/include",
        ]

        for arg in context.compile_args:
            if arg.startswith("-I"):
                search_dirs.insert(0, arg[2:].strip())

        for sdir in search_dirs:
            candidate = os.path.join(sdir, header_name)
            if os.path.isfile(candidate):
                return DefinitionLocation(
                    file_path=os.path.abspath(candidate), line=1, column=1
                )

        return None

    def get_definition(self, context: CContext) -> Optional[DefinitionLocation]:
        tu = self._parse_translation_unit(context)
        file_path = context.file_path or "unsaved_buffer.c"

        if not tu:
            return self._fallback_include_definition(context)

        target_file = tu.get_file(file_path)
        if not target_file:
            return self._fallback_include_definition(context)

        location = tu.get_location(file_path, (context.line, context.col))
        cursor = Cursor.from_location(tu, location)

        if not cursor or cursor.kind == CursorKind.TRANSLATION_UNIT:
            return self._fallback_include_definition(context)

        # Handle header inclusions explicitly
        if cursor.kind == CursorKind.INCLUSION_DIRECTIVE:
            try:
                inc_file = cursor.get_included_file()
                if inc_file and inc_file.name:
                    return DefinitionLocation(
                        file_path=str(inc_file.name),
                        line=1,
                        column=1,
                        context_line=None,
                    )
            except Exception:
                pass
            return self._fallback_include_definition(context)

        referenced = cursor.referenced
        if referenced is None or referenced.kind == CursorKind.TRANSLATION_UNIT:
            try:
                referenced = cursor.get_definition()
            except Exception:
                referenced = None

        if referenced is None or referenced.kind == CursorKind.TRANSLATION_UNIT:
            return self._fallback_include_definition(context)

        if referenced.location is None or referenced.location.file is None:
            return None

        loc = referenced.location
        if str(loc.file.name) == file_path and int(loc.line) == context.line:
            return None

        return DefinitionLocation(
            file_path=str(loc.file.name),
            line=int(loc.line),
            column=int(loc.column),
            context_line=None,
        )

    def get_completions(self, context: CContext) -> List[CompletionDetails]:
        tu = self._parse_translation_unit(context)
        if not tu:
            return []

        file_path = context.file_path or "unsaved_buffer.c"
        unsaved_files = [(file_path, context.source_code)]

        try:
            results = tu.codeComplete(
                file_path,
                context.line,
                context.col,
                unsaved_files=unsaved_files,
                include_brief_comments=True,
            )
        except Exception as e:
            logger.warning("Clang codeComplete failed: %s", str(e))
            return []

        if not results:
            return []

        completions: List[CompletionDetails] = []
        for item in results.results:
            typed_text = ""
            signature_parts = []

            for chunk in item.string:
                if chunk.isKindTypedText():
                    typed_text = chunk.spelling
                if chunk.isKindPlaceHolder() or chunk.isKindInformative():
                    signature_parts.append(chunk.spelling)

            if not typed_text:
                continue

            completions.append(
                CompletionDetails(
                    text=typed_text,
                    insert_text=typed_text,
                    kind=self._completion_kind(item.cursorKind),
                    signature=" ".join(signature_parts),
                )
            )

        return completions

    def get_diagnostics(self, context: CContext) -> List[CDiagnostic]:
        tu = self._parse_translation_unit(context)
        if not tu:
            return []

        diagnostics: List[CDiagnostic] = []
        for diag in tu.diagnostics:
            if diag.location.file is None:
                continue

            if diag.severity >= 3:
                severity_str = "Error"
                color_hex = "#FF5555"
            elif diag.severity == 2:
                severity_str = "Warning"
                color_hex = "#FFB86C"
            else:
                severity_str = "Note"
                color_hex = "#8BE9FD"

            start_col = max(0, diag.location.column - 1)
            end_col = start_col + 1
            if diag.option:
                end_col = start_col + len(diag.spelling)

            diagnostics.append(
                CDiagnostic(
                    line=diag.location.line,
                    start_col=start_col,
                    end_col=end_col,
                    severity=severity_str,
                    message=diag.spelling,
                    color=color_hex,
                )
            )

        return diagnostics
