"""
Analysis server standalone entry point for PyInstaller frozen builds.

This is a tiny wrapper around editor.Ironica.analysis_server.main()
so PyInstaller can build a clean second executable:
DreamStudioAnalysisServer

The server protocol (pickle frames over stdin/stdout) is unchanged.
"""
from editor.Ironica.analysis_server import main

if __name__ == "__main__":
    raise SystemExit(main())
