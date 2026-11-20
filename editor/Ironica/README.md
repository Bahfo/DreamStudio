# Ironica Code Editor

© COPYRIGHT 2026 Gizmo MicroSystems - All Rights Reserved.
This part of the repository contains all source codes related to the DreamStudio Ironica Code Editor. 

## Table of Contents
1. What is Ironica. 
2. Ironica Inside of DreamStudio.
3. Using Ironica outside of the IDE. 
4. Licensing Terms.

## 1. What is Ironica
Ironica is the core engine built around Scintilla, providing the core editor modules and methods used by DreamStudio to open, edit, highlight, and preview code files and other file formats. 

Ironica is copyrighted to Gizmo MicroSystems, and is built by Bahaa Nofal. The source code of Ironica is available within this folder and licensed within the [LICENSE](/editor/Ironica/LICENSE.md) terms. 

Ironica's name came actually from the word *Ironic*. Because the author did not expect to build a very strong engine, after all, his initial expectation was to get a good engine, but not as good as it was after building it, it was *Ironic* how it was expected to be, and how it went down. It was a surprise for the author that Scintilla was powerful enough by itself to handle large files that a user may open. 

Anyway, the Ironica code editor has the following features built-in by default: 
1. Syntax Highlighting: Featuring highlighting for a wide set of languages, including Python, C and C++, Java, JavaScript, B-Sharp, and many others, in addition to highlighting of custom scripting languages such as Bash, Powershell, HTML, CSS, JSON, Markdown, and more.
2. Autocompletion: Featured for Python, C, C++, and B#. 
3. Analysis Managers: Analysis Server and Worker for Python, C, C++, and B#. 
4. Custom built-in themes for syntax highlighting. 
5. Code snippets engine for fast addition of code snippets. 
6. Custom features such as folding, imports highlighting, underlining for errors and warnings. 
7. Documentation Flyout and Go-To-Definition Engine. 
8. Video and Image viewers and editors.
9. Minimap, hover controller, a diagnostics ruler, a web browsers, an in-files browser, and many more.

## 2. Ironica Inside of DreamStudio
*It is Ironic, isn't it?*

Ironica is the core editor of DreamStudio, all of your opened files, including images, videos, PDFs, etc. are all opened within Ironica. It has a custom-made tabs editor, in addition to all tools required to edit and modify or view the specific file by type and extension. 

## 3. Ironica Outside of DreamStudio
*Ironica is made to math iron's strength*

Ironica is used also in OpenBox Studio, the agentic development environment. Ironica also appears inside SciLab software, which is the software used to calculate `'scientifically'` you engineering tasks. 

## 4. Licensing Terms
Read the [LICENSE](/editor/Ironica/LICENSE.md) for more info.