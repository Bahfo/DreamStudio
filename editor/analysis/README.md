# DreamStudio Analyzer Module

## Getting Started
#### Requirements
Read repository's `README.md` to find out specific requirements.

This module is written in D-lang. It performs static analysis on Ironica's opened source code files. 

**What it does**
1. Code diagnostics. 
2. Outlining symbols.
3. Resolving.
4. Code analysis. 
5. Parsing and Tree generation.

To build, since the dynamic libraries are not included by default. Run: 

```bash
dub build --build=release
```