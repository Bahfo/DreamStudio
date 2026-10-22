# AI Agent Coding Instructions & Repository Rules

You are an expert Python developer contributing to this repository. You must strictly adhere to the following stylistic, structural, and architectural rules for every code modification or file creation.

## 1. File Headers & Copyright (Mandatory for New Scripts)
Every single new Python script must start with the exact copyright header format below. Replace `<brief description>` with a clear, one-two sentence explanation of the file's purpose.

```python
"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved. 

<brief description of what this file is for>
"""
```

## 2. Code Geometry & Line Length
* The absolute maximum line length is 110 columns (characters). 
* Do not exceed 110 characters for code, comments, or docstrings. Wrap lines cleanly.

## 3. Documentation Requirements
* **Objects (Classes):** Every class must have a high-level docstring explaining its responsibility and main attributes.
* **Methods/Functions:** Every public method and standalone function must have a docstring detailing its purpose, parameters (`Args:`), and return value (`Returns:`).
* Use Google-style or Sphinx-style docstrings consistently.

## 4. Commenting Strategy
Keep the codebase clean. Do not write narrative comments explaining *how* the code works (the code itself should be self-documenting).
* **Allowed comments:** Small, precise inline explanations for complex algorithms, `TODO:` items for future enhancements, and `NOTE:` items for critical edge cases.
* Avoid redundant comments like `# increment x by 1`.

## 5. Standard Python Formatting Rules (PEP 8+)
* **Naming Conventions:** 
  * Modules/Packages: `snake_case.py`
  * Classes: `PascalCase`
  * Functions/Methods: `PascalCase`, `camelCase`, or `snake_case`
  * Variables: `snake_case`
  * Constants: `UPPER_CASE_SNAKE`
* **Imports:** Group imports logically (Standard library -> Third-party -> Local imports). Absolute imports are preferred over relative imports.
* **Typing:** Provide explicit Python type hints for all function arguments and return types wherever possible.