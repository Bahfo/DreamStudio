"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

CMake language plugin, sorted by mission.

Watched surface (stays outside, loaded as one unit by ``provider``):

- ``provider.py`` — plugin entry (``create_provider``).
- ``keywords/cmake.json`` — lexer keywords, extensions and filenames.
- ``snippets/cmake.json`` — snippet bodies surfaced by completion.

Mission packages:

- ``cmake`` — CMakeLists scanner and compile database generator feeding
  the C++ plugin (``scanner.py``, ``generator.py``).
"""
