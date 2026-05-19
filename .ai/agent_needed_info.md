# Project Context & Architecture Mapping

DreamJetPack/
├── .ai/
├── .git/
│   ├── opencode
│   ├── ORIG_HEAD
│   ├── packed-refs
│   └── refs
├── .gitattributes
├── .gitignore
├── .vscode/
│   └── settings.json
├── assets/
│   ├── activities/
│   ├── editor/
│   ├── logos/
│   ├── menus/
│   ├── system/
│   ├── themes/
│   └── types/
│
├── bash_commands.bash
├── build_version.json
├── changes.txt
├── clear_cache.bash
├── clear_cache.ps1
├── consoles_emulators/
│   ├── EXConsole_TitanAlpha01/
│   │   └── ui_setup.py
│   └── EXConsole_Titanium512/
│       ├── __init__.py
│       └── ui_setup.py
├── ddocs/
│   ├── docs/
│   │   ├── dreamstudio/
│   │   │   └── welcome.dsman
│   │   ├── frameworks/
│   │   │   └── IronKinter/
│   │   │       └── intro_to_ironkinter.dsman
│   │   ├── get_started.dsman
│   │   ├── help.dsman
│   │   └── manual.pdf
│   ├── manual.d
│   └── menubar.d
├── documentation/
│   ├── contributions.ipynb
│   ├── getting_started.ipynb
│   └── keybindings_reference.md
├── editor/
│   ├── animations/
│   │   └── splash.py
│   ├── css_styles/
│   │   └── main.qss
│   ├── init/
│   │   ├── __init__.py
│   │   ├── initialize.py
│   │   └── project_bootstrap.py
│   ├── terminal/
│   │   ├── __init__.py
│   │   ├── PromptXEngine.py
│   │   ├── PromptXShellGUIClass.py
│   │   ├── shell.py
│   │   └── terminal_ui.py
│   ├── texteditor/
│   │   ├── __init__.py
│   │   ├── assets/
│   │   │   ├── next.png
│   │   │   ├── pause.png
│   │   │   ├── play.png
│   │   │   ├── previous.png
│   │   │   ├── reset.png
│   │   │   ├── stop.png
│   │   │   ├── zoom_in.png
│   │   │   └── zoom_out.png
│   │   ├── clangd.py
│   │   ├── code_editor.py
│   │   ├── ImageViewer.py
│   │   ├── ironica_lexer/
│   │   │   ├── completion.py
│   │   │   ├── cpp_lexer.py
│   │   │   ├── json_lexer.py
│   │   │   └── python_lexer.py
│   │   ├── json_editor.py
│   │   ├── keywords/
│   │   │   ├── cpp.json
│   │   │   └── python.json
│   │   ├── markdown_editor.py
│   │   ├── minimap.py
│   │   ├── PDFViewer.py
│   │   └── tab_editor.py
│   ├── ui_build.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── build_status.py
│   │   ├── etherAI.py
│   │   ├── fast_tutorial.py
│   │   ├── file_explorer.py
│   │   ├── find_replace.py
│   │   ├── optionsBar.py
│   │   ├── shortcuts.json
│   │   ├── statusBar.py
│   │   └── titleBar.py
│   └── widgets/
│       ├── __init__.py
│       ├── QActivityButton.py
│       ├── QCustomLabels.py
│       ├── QCustomTitleBar.py
│       ├── QExitDialog.py
│       ├── QIconsProvider.py
│       └── QTitleBar.py
├── interface.py
├── internet/
│   └── techNews/
│       ├── news.css
│       ├── news.html
│       ├── news.js
│       └── news.json
├── LICENSE
├── README.md
├── requirements.txt
├── run.py
├── scripts/
│   └── clear.bash
├── shells/
│   ├── __init__.py
│   ├── build_utils/
│   │   ├── definitions.h
│   │   ├── loop.c
│   │   ├── task_builder/
│   │   │   ├── clean_cache.cpp
│   │   │   └── search_files.cpp
│   │   └── welcome.c
│   ├── daydream.py
│   └── file_manager/
│       └── file_manager.d
└── welcome.py