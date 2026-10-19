"""Analysis server standalone entry point for PyInstaller frozen builds."""
from editor.Ironica.analysis_server import main

if __name__ == "__main__":
    raise SystemExit(main())
