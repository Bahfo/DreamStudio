"""
Concrete implementation of the IJediAdapter interface using the jedi library.
This file encapsulates all interactions with Jedi, ensuring no raw Jedi objects
or exceptions leak into the rest of the application.
"""

import logging
import jedi

from typing import List, Optional

from .domain_models import (
    PythonContext,
    CompletionItem,
    HoverDetails,
    ParameterInfo,
    DefinitionLocation,
    ReferenceLocation,
    RefactorChange,
)
from .interfaces import IJediAdapter

logger = logging.getLogger("DreamStudio.PythonSupport.JediAdapter")


class JediAdapter(IJediAdapter):
    """
    An adapter that translates between the DreamStudio domain layer and Jedi.
    This class is stateless and operates strictly on the provided PythonContext.
    """

    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def _extract_default_from_signature(param) -> Optional[str]:
        """Extract default value from a Jedi parameter's signature string.

        Jedi's param.to_string() returns e.g. ``b=10`` or ``c="hello"``.
        This extracts the value after the ``=``.
        """
        try:
            param_str = param.to_string()
            if "=" in param_str:
                default_part = param_str.split("=", 1)[1].strip()
                if default_part:
                    return default_part
        except Exception:
            pass
        return None

    def _get_script(self, context: PythonContext) -> Optional[jedi.Script]:
        """
        Safely instantiates a Jedi Script from an immutable context.
        The subsystem does not touch the filesystem; code is passed purely in memory.
        """
        try:
            return jedi.Script(
                code=context.source_code,
                path=context.file_path,
            )
        except Exception as e:
            logger.error(
                "Failed to instantiate Jedi Script. Context file_path: %s. Error: %s",
                context.file_path,
                str(e),
                exc_info=True,
            )
            return None

    def get_completions(self, context: PythonContext) -> List[CompletionItem]:
        """
        Queries Jedi for completions and maps them to domain CompletionItems.
        Guarantees no raw Jedi objects or exceptions escape.
        """
        script = self._get_script(context)
        if not script:
            return []

        try:
            jedi_completions = script.complete(line=context.line, column=context.column)

            results: List[CompletionItem] = []
            for item in jedi_completions:
                try:
                    # Capture documentation safely to avoid rendering slowdowns later
                    doc = item.docstring(raw=True)
                    results.append(
                        CompletionItem(
                            label=item.name,
                            insert_text=item.name_with_symbols,
                            kind=item.type,
                            documentation=doc if doc else None,
                        )
                    )
                except Exception as inner_ex:
                    logger.warning(
                        "Failed parsing individual completion item '%s': %s",
                        item.name,
                        str(inner_ex),
                    )
                    # Fallback to a bare-minimum model if extraction of details fails
                    results.append(
                        CompletionItem(
                            label=item.name,
                            insert_text=item.name,
                            kind="value",
                            documentation=None,
                        )
                    )
            return results

        except Exception as e:
            logger.error("Jedi completion execution failed: %s", str(e), exc_info=True)
            return []

    def get_hover(self, context: PythonContext) -> Optional[HoverDetails]:
        """
        Queries Jedi to parse detailed tooltip and signature data at the cursor position.
        """
        script = self._get_script(context)
        if not script:
            return None

        try:
            definitions = script.help(line=context.line, column=context.column)
            if not definitions:
                # Fallback to type inference if standard help yields nothing
                definitions = script.infer(line=context.line, column=context.column)

            if not definitions:
                return None

            primary_def = definitions[0]

            # Parse parameters if the symbol is callable (function, class, method)
            parameters: List[ParameterInfo] = []
            signature_str = ""
            return_type = None

            signatures = primary_def.get_signatures()
            if signatures:
                sig = signatures[0]
                signature_str = sig.to_string()

                # Parse return type from type annotation if present
                if hasattr(sig, "annotation") and sig.annotation:
                    return_type = str(sig.annotation)

                # Parse parameter specific names, defaults, and hints
                for param in sig.params:
                    annotation = (
                        param.annotation if hasattr(param, "annotation") else None
                    )
                    default = None
                    if hasattr(param, "default"):
                        default = param.default
                    if default is None:
                        default = JediAdapter._extract_default_from_signature(param)
                    parameters.append(
                        ParameterInfo(
                            name=param.name,
                            type_hint=str(annotation) if annotation else None,
                            default_value=str(default) if default else None,
                        )
                    )
            else:
                # Fallback to simple definition representation if no signature exists
                signature_str = primary_def.description

            return HoverDetails(
                name=primary_def.name,
                kind=primary_def.type,
                signature=signature_str,
                parameters=parameters,
                return_type=return_type,
                docstring=primary_def.docstring() or None,
            )

        except Exception as e:
            logger.error("Jedi hover analysis failed: %s", str(e), exc_info=True)
            return None

    def get_definition(self, context: PythonContext) -> Optional[DefinitionLocation]:
        """
        Traces the execution back to the target definition location.
        """
        script = self._get_script(context)
        if not script:
            return None

        try:
            # Trace the reference definition assignment
            definitions = script.goto(line=context.line, column=context.column)
            if not definitions:
                # Analytical infer fallback
                definitions = script.infer(line=context.line, column=context.column)

            if not definitions:
                return None

            target = definitions[0]

            # Extract raw paths securely and convert to standardized strings
            file_path = str(target.module_path) if target.module_path else None

            # Capture the target code context snippet surrounding the definition target
            context_line = None
            try:
                context_line = target.get_line_code()
            except Exception:
                pass  # Suppress and keep as None if code lookup fails

            return DefinitionLocation(
                file_path=file_path,
                line=int(target.line) if target.line else 1,
                column=int(target.column) if target.column else 0,
                context_line=context_line,
            )

        except Exception as e:
            logger.error("Jedi goto definition trace failed: %s", str(e), exc_info=True)
            return None

    def get_references(self, context: PythonContext) -> List[ReferenceLocation]:
        """
        Retrieves reference locations from Jedi and translates them to domain models.
        """
        script = self._get_script(context)
        if not script:
            return []

        try:
            # Query Jedi for usages of the symbol under the cursor
            jedi_refs = script.get_references(line=context.line, column=context.column)

            results: List[ReferenceLocation] = []
            for ref in jedi_refs:
                try:
                    file_path = (
                        str(ref.module_path) if ref.module_path else context.file_path
                    )
                    line_code = ref.get_line_code() or ""

                    # Compute length of symbol to allow UI highlighting
                    symbol_length = len(ref.name)

                    results.append(
                        ReferenceLocation(
                            file_path=file_path,
                            line=ref.line if ref.line else 1,
                            column=ref.column if ref.column else 0,
                            context_line=line_code.strip(),
                            symbol_length=symbol_length,
                        )
                    )
                except Exception as inner_ex:
                    logger.warning(
                        "Failed parsing reference on line %s: %s",
                        getattr(ref, "line", "unknown"),
                        str(inner_ex),
                    )
                    continue
            return results

        except Exception as e:
            logger.error("Jedi references search failed: %s", str(e), exc_info=True)
            return []

    def get_rename_changes(
        self, context: PythonContext, new_name: str
    ) -> List[RefactorChange]:
        """
        Invokes Jedi's refactoring engine to safely retrieve renaming actions.
        Returns empty results on any collision or refactoring exception.
        """
        script = self._get_script(context)
        if not script:
            return []

        try:
            # Perform renaming calculation
            refactoring = script.rename(
                line=context.line, column=context.column, new_name=new_name
            )

            changes: List[RefactorChange] = []
            for path, changed_file in refactoring.get_changed_files().items():
                try:
                    changes.append(
                        RefactorChange(
                            file_path=str(path) if path else context.file_path,
                            new_source_code=changed_file.get_new_code(),
                        )
                    )
                except Exception as inner_ex:
                    logger.warning(
                        "Failed extracting refactored source for %s: %s",
                        path,
                        str(inner_ex),
                    )
            return changes

        except Exception as e:
            # Captures RefactoringError safely without leaking external exceptions
            logger.error("Jedi rename execution failed: %s", str(e), exc_info=True)
            return []
