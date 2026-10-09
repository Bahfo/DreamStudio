"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

C++ language plugin, sorted by mission.

Watched surface (stays outside, loaded as one unit by ``provider``):

- ``provider.py`` — plugin entry (``create_provider``) and watcher.
- ``models.py`` — shared domain contract used by every mission.

Mission packages:

- ``autocompletion`` — trigger classification, completion bridging,
  preprocessor sources, symbol table, call-site intelligence.
- ``intellisense`` — libclang engine and compile-flag resolution.
- ``navigation`` — reserved: go-to-definition, references, callers.
- ``errors_detection`` — reserved: diagnostics, problems feed.
- ``folding`` — reserved: fold regions.
- ``highlighting`` — reserved: semantic highlighting.
- ``quick_fixes`` — reserved: code actions and assists.
"""
