# Python Plugin Test Suite

## Overview
Comprehensive coverage for the Python language plugin: domain models, interfaces, cache policy, provider hover/navigation/completion surfaces, real and scripted Jedi behaviour, outline parsing, semantic highlighting, folding, diagnostics, completions, plugin registration, analysis-server dispatch, and the whole-document analysis manager. Includes timing-only performance coverage for Python files larger than 10,000 lines.

## Latest Run

- **Run ID**: 20261027T175027Z-1f8c0fb-dirty
- **Timestamp**: 2026-10-27T17:50:27Z
- **Verdict**: PASSED
- **Passed**: 591 | **Failed**: 0 | **Errors**: 0 | **Skipped**: 0 | **Blocked**: 0
- [Report](../reports/runs/20261027T175027Z-1f8c0fb-dirty/report.md)

## Historical Runs

| Run ID | Timestamp | Verdict | Passed | Failed | Errors | Skipped | Blocked | Report |
|--------|-----------|---------|--------|--------|--------|---------|---------|--------|
| 20261027T175027Z-1f8c0fb-dirty | 2026-10-27T17:50:27Z | PASSED | 591 | 0 | 0 | 0 | 0 | [Report](../reports/runs/20261027T175027Z-1f8c0fb-dirty/report.md) |
| 20261027T172526Z-1f8c0fb-dirty | 2026-10-27T17:25:26Z | PASSED | 591 | 0 | 0 | 0 | 0 | [Report](../reports/runs/20261027T172526Z-1f8c0fb-dirty/report.md) |
| 20261027T171422Z-1f8c0fb-dirty | 2026-10-27T17:14:22Z | PASSED | 591 | 0 | 0 | 0 | 0 | [Report](../reports/runs/20261027T171422Z-1f8c0fb-dirty/report.md) |

## Scope & Limitations

### In scope
- `editor/Ironica/plugins/python/domain_models.py` — context, hover, definition, reference, and completion models
- `editor/Ironica/plugins/python/interfaces.py` — adapter/provider/service contracts
- `editor/Ironica/plugins/python/cache.py` — key construction, eviction order, hit/miss policy, zero/negative capacity
- `editor/Ironica/plugins/python/provider.py` — hover hints/display, go-to-definition, completions, formatting, folding/outline delegation, manager factories
- `editor/Ironica/plugins/python/jedi_adapter.py` — script/project resolution, hover/definition/completion mapping, fallbacks, real Jedi integration
- `editor/Ironica/plugins/python/outline_parser.py` — imports, assignments, classes, methods, decorators, signatures, positions, encodings, and the O(file size) segment regression
- `editor/Ironica/plugins/python/semantic_highlights.py` — lexical tokens, AST overlays, syntax fallback, byte offsets, exclusions, dedupe, cache/theme lifecycle
- `editor/Ironica/plugins/python/folding.py` — function/class/import regions, decorators, strings, indentation, import labels
- `editor/Ironica/plugins/python/jedi_worker.py` — syntax diagnostics, span merging, diagnostics/completions managers, workers, fallbacks, shutdown
- `editor/Ironica/plugins/registration.py` — legacy bundled Python plugin discovery, factory import, outline registration
- `editor/Ironica/analysis_server.py` — diagnostics/completions/analysis request handlers and workspace path handling
- `editor/Ironica/analysis_worker.py` — in-process analysis, remote bridge payloads, manager result application/cleanup
- Large-file performance (>10,000 lines) for outline, semantic highlights, folding, syntax diagnostics, analysis-server requests, real Jedi hover/definition/completions, and the definition cache

### Out of scope
- Launching the real analysis subprocess and exercising OS-level framing/transport
- Editor widget rendering beyond minimal Qt/editor doubles (tooltip painting, theme appearance)
- Cross-file Jedi indexing and third-party package resolution
- C/C++ and CMake plugin behaviour
- Subjective UI/UX judgements and screenshot comparison

### Known limitations recorded by this suite
- `PythonContext` is documented as immutable but is not a frozen dataclass
- `LanguageCache.set()` deliberately does not overwrite an existing key
- A Jedi `help` exception aborts hover instead of falling back to `infer`
- Folded multiline decorators and parenthesised imports are not detected as fold starts
- Syntax diagnostics are capped at `_MAX_DIAGNOSTICS` entries
- Real Jedi results are version-sensitive (suite runs against Jedi 0.20.0)

### Performance reporting
- Timings are wall-clock samples collected by the suite-local `timing_recorder`
- The terminal summary prints run count, median, minimum, and maximum milliseconds
- **No pass/fail threshold is asserted on elapsed time**; correctness assertions remain independent of timing

### Manual verification needed
- Tooltip/flyout rendering and theme colours in a real editor
- Behaviour of the real analysis subprocess under memory pressure
- Cross-file navigation inside a real project workspace

## Failure Reproduction
To reproduce failures from this run:
```bash
./tests/run_tests.sh --suite python_plugin
```

Or directly with pytest:
```bash
QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest tests/python_plugin_test/ -p no:cacheprovider -q
```

To run only the large-file performance measurements:
```bash
QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest tests/python_plugin_test/test_performance_10k_lines.py -p no:cacheprovider -q -m performance
```
