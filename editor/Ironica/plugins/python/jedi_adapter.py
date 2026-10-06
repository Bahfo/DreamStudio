"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Jedi integration adapter for DreamStudio.
"""

from editor import *
import jedi

from .domain_models import (
    PythonContext,
    HoverDetails,
    ParameterInfo,
    DefinitionLocation,
    CompletionDetails,
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
            project = self._resolve_project(context)
            if project is not None:
                return jedi.Script(
                    code=context.source_code,
                    path=context.file_path,
                    project=project,
                )
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

    @staticmethod
    def _resolve_project(context: PythonContext):
        """Build a Jedi project rooted at the user's project directory.

        Falls back to the buffer's own directory when no project root
        was supplied, and returns ``None`` when neither is available
        so callers keep the previous behaviour.
        """
        import os

        candidates: list = []
        file_dir = None
        if context.file_path:
            try:
                file_dir = os.path.dirname(os.path.abspath(context.file_path))
            except Exception:
                file_dir = None
        project_root = None
        if getattr(context, "project_root", None):
            try:
                project_root = os.path.abspath(context.project_root)
            except Exception:
                project_root = None
        for candidate in (file_dir, project_root):
            if candidate and os.path.isdir(candidate):
                if candidate not in candidates:
                    candidates.append(candidate)
        if not candidates:
            return None
        root = project_root or file_dir
        try:
            return jedi.Project(path=root, added_sys_path=candidates)
        except Exception:
            return None

    def get_hover(self, context: PythonContext) -> Optional[HoverDetails]:
        """
        Queries Jedi to parse detailed tooltip and signature data at the cursor position.
        """
        script = self._get_script(context)
        if not script:
            return None

        try:
            try:
                jedi_line = context.line
                definitions = script.help(line=jedi_line, column=context.column)
                if not definitions:
                    definitions = script.infer(line=jedi_line, column=context.column)
            except Exception as e:
                logger.warning("Jedi subprocess hover failed: %s", e)
                return None

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
            try:
                try:
                    definitions = script.goto(
                        line=context.line,
                        column=context.column,
                        follow_imports=True,
                    )
                except TypeError:
                    definitions = script.goto(
                        line=context.line, column=context.column
                    )
                if not definitions:
                    definitions = script.infer(line=context.line, column=context.column)
            except Exception as e:
                logger.warning("Jedi subprocess goto failed: %s", e)
                return None

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

    def get_completions(self, context: PythonContext) -> List[CompletionDetails]:
        """Return code-completion suggestions at the cursor position.

        Delegates to ``jedi.Script.complete()`` and translates each raw
        Jedi completion object into a ``CompletionDetails`` domain model.
        """
        script = self._get_script(context)
        if not script:
            return []

        try:
            jedi_completions = script.complete(
                line=context.line,
                column=context.column,
            )
        except Exception as e:
            logger.warning("Jedi complete failed: %s", e)
            return []

        results: List[CompletionDetails] = []
        for comp in jedi_completions:
            try:
                sig_parts: List[str] = []
                for sig in comp.get_signatures():
                    sig_parts.append(sig.to_string())
                signature = ", ".join(sig_parts)
            except Exception:
                signature = ""

            results.append(
                CompletionDetails(
                    text=comp.name,
                    # NOTE: comp.complete is only the missing suffix; callers
                    # replace the typed prefix, so insert the full word.
                    insert_text=comp.name,
                    kind=comp.type or "",
                    signature=signature,
                )
            )

        return results
