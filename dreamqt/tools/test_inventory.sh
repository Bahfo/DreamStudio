# (C) COPYRIGHT 2026 Gizmo MicroSystems - All Rights Reserved. 
# Grabs the testing inventory of Qt.

rg --files \
  -g 'pytest.ini' \
  -g 'tox.ini' \
  -g 'pyproject.toml' \
  -g 'setup.cfg' \
  -g 'unittest*.py' \
  -g '!dreamqt/**' \
  -g '!venv/**' \
  -g '!.venv/**' \
  .