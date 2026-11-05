# C++ Plugin Test Suite

## Structure

| File | Purpose |
|------|---------|
| `test_hover.py` | Hover extraction, Markdown formatting, provider integration |
| `test_cross_file_hover.py` | Header discovery and cross-file docs (templates, macros, methods) |

## Running Tests

```bash
# Run C++ plugin tests
./tests/run_tests.sh --suite cpp_plugin

# Run specific test module
QT_QPA_PLATFORM=offscreen python -m pytest tests/cpp_plugin_test/test_hover.py -v
```

## Test Categories

- **Unit tests** (fast, no libclang): Model validation, Markdown formatting
- **Integration tests** (require libclang + compile_commands.json): Full hover extraction

Integration tests are marked with `@pytest.mark.integration` and skipped by default.
Run with `-m integration` to enable.
