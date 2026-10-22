# Editor Model — DreamStudio IDE

> **Purpose**: how documents, tabs, dirty state, encoding, cursor/selection, folding, and the per-tab provider wiring actually work.

---

## 1. The Object Graph

```
DreamTabbedEditor (QTabWidget)                     editor/Ironica/tab_editor.py:28
│   owned by
├── EditorContainer (QWidget)                       editor/Ironica/ui_build.py:44
│       owned by
│   └── WorkspaceContainer                          editor/workspace_container.py:28
│
└── per tab:
    ├── MiniMapHostWidget                           editor/Ironica/utils/minimap.py
    │       └── CodeEditor (QsciScintilla)          editor/Ironica/code_editor.py:26
    │               ├── current_provider            (BaseLanguageProvider)
    │               ├── _diag_manager               (provider diagnostic manager)
    │               ├── _completion_manager         (provider completion manager)
    │               └── _analysis_manager           (whole-document analysis)
    ├── FallBack (QWidget)                         editor/Ironica/tab_editor.py:1043
    │       └── used for files that fail to decode/load
    ├── binary editor                               (ELF / binary viewer)
    └── diff tab / preview tab / welcome tab
```

### Two tabs, three shapes

A tab is **not** always a `CodeEditor`:

| Tab content | When | How to detect |
|---|---|---|
| `MiniMapHostWidget` | Normal text file | `isinstance(widget, MiniMapHostWidget)` |
| `FallBack` | The file failed to load (decode error, OS error) | `DreamTabbedEditor._is_fallback(widget)` (`tab_editor.py:462`) |
| Binary editor | The file is an ELF binary (`_is_elf_binary`, `tab_editor.py:336`) | `add_binary_editor` |

**Always unwrap** with `DreamTabbedEditor._unwrap_code_editor(widget)` (`tab_editor.py:682`) or `editor.Ironica.utils.minimap.ensure_inner(widget)`. Never `isinstance(widget, CodeEditor)`.

---

## 2. Document Identity

### 2.1 The dedup key

```python
DreamTabbedEditor.resolve_key(file_path)          # tab_editor.py:911
    → os.path.normcase(os.path.normpath(file_path))
```

- One tab per normalised path. Opening the same file twice **activates** the existing tab instead of creating a second one (`add_new_editor`, `tab_editor.py:476-482`).
- Untitled tabs get `f"__untitled_{id(new_editor)}"` (`tab_editor.py:539`).
- `self.opened_files: dict[str, int]` maps key → tab index. It is the authoritative "is this file open?" registry.

> `normcase` makes the key case-insensitive on Windows and case-sensitive on POSIX. Do not "fix" this to always lowercase — it would merge two distinct files on Linux/macOS.

### 2.2 The file path on the editor

`CodeEditor.current_file_path` is set by `load_from_file` (`code_editor.py:2195`) and is the path used by diagnostics, git status, the run controller, and the debugger.

---

## 3. Tab Lifecycle

### 3.1 Open

```
tabs.open_file_by_path(path)                        tab_editor.py:816
 └─ add_new_editor(file_path=path, ...)
     ├─ key = resolve_key(path)
     ├─ if key in opened_files → setCurrentIndex(existing) and return
     ├─ if _is_elf_binary(path) → add_binary_editor(...)
     ├─ try:
     │     code_editor = CodeEditor(self, language=language)
     │     code_editor.load_from_file(path)
     │     new_editor = MiniMapHostWidget(code_editor, parent=self)
     │  except (UnicodeDecodeError, OSError, ValueError):
     │     new_editor = FallBack(self); new_editor.setText(content)   # never crash
     ├─ attach status-bar analysis spinner (analysis_started / analysis_finished)
     ├─ if provider.has_diagnostics():
     │     code_editor._diag_manager = provider.create_diagnostic_manager(...)
     ├─ if provider has create_completion_manager:
     │     code_editor._completion_manager = provider.create_completion_manager(...)
     │     _schedule_completion_warmup(code_editor, file_path)   # QTimer.singleShot(500, …)
     ├─ index = addTab(new_editor, file_name); setCurrentIndex(index)
     ├─ new_editor.file_key = key; opened_files[key] = index
     ├─ connect dirty_state_changed → _on_editor_dirty_changed_explicit
     ├─ tabBar().rebuild_dirty_indices()
     └─ if new_editor.isReadOnly(): tabBar().mark_readonly(index, True)
```

### 3.2 Close

```
tabCloseRequested → _on_close_requested(index)     tab_editor.py:642
 ├─ if code_editor.isModified():
 │     UnsavedChangesDialog(dirty_files=[tab_name])
 │     ├─ RESULT_CANCEL → abort, tab stays open
 │     ├─ RESULT_SAVE   → code_editor.save(); on failure → notification, tab stays open
 │     └─ otherwise (discard) → continue
 └─ close_editor(index)                            tab_editor.py:691
     ├─ run every registered close interceptor (cb(index, editor) → False aborts)
     ├─ stop the active debug session if it targets this file
     ├─ disconnect dirty_state_changed
     ├─ code_editor._diag_manager.shutdown()
     ├─ code_editor._completion_manager.shutdown()
     ├─ code_editor._analysis_manager.shutdown()
     ├─ disconnect analysis_started / analysis_finished / textChanged
     ├─ code_editor._teardown_hover_engine()
     ├─ remove from opened_files
     └─ tabBar().rebuild_dirty_indices()
```

**Every teardown is individually wrapped in `try/except`.** A failing manager must never prevent the tab from closing.

### 3.3 Save

| Method | Behaviour |
|---|---|
| `CodeEditor.save()` (`code_editor.py:1961`) | Writes the buffer to `current_file_path`, clears the dirty flag, emits `dirty_state_changed(False)`, clears save indicators, and notifies the git status service. |
| `tabs.save_current_file()` (`tab_editor.py:919`) | Saves the active tab. If the tab is untitled, delegates to `save_current_file_as()`. |
| `tabs.save_current_file_as()` (`tab_editor.py:940`) | Opens a save dialog, re-keys the tab in `opened_files`, and re-opens the saved tab. |
| `tabs.save_all_files()` (`tab_editor.py:973`) | Saves every tab with a path. |

---

## 4. Dirty State

### 4.1 Single source of truth

`CodeEditor._is_dirty` (`code_editor.py:81`) is the authoritative flag.

| Operation | Effect |
|---|---|
| `_on_text_changed` (`code_editor.py:219`) | If not already dirty → `_is_dirty = True` and emit `dirty_state_changed(True)`. |
| `clear_dirty()` (`code_editor.py:271`) | `_is_dirty = False`. |
| `is_dirty()` (`code_editor.py:284`) | Read-only accessor. |
| `mark_document_saved()` (`code_editor.py:806`) | Resets the Scintilla "modified" flag and the save indicators. |
| `load_from_file` (`code_editor.py:2203-2213`) | Resets `_is_dirty`, emits `dirty_state_changed(False)`. |

### 4.2 The tab marker is a mirror

`DreamStudioIDETabBar` keeps two sets: `_dirty_indices` and `_readonly_indices`.

| API | Line | Purpose |
|---|---|---|
| `mark_dirty(index, is_dirty)` | 329 | Add/discard the index and repaint that tab rect. |
| `mark_readonly(index, is_readonly)` | 338 | Same for the lock glyph. |
| `rebuild_dirty_indices()` | 361 | Re-derive `_dirty_indices` from `widget(i).is_dirty()`. |
| `rebuild_readonly_indices()` | 364 | Re-derive `_readonly_indices` from `widget(i).isReadOnly()`. |

**Whenever the tab order or the tab set changes, call `rebuild_dirty_indices()`.** The index-based sets go stale after a reorder or a close. `tab_editor.py` calls it after: `add_new_editor` (558), `close_editor` (770), `save_current_file` (933/938), `save_current_file_as` (954/960), `save_all_files` (990).

The tab bar paints the dirty dot and the lock icon inside `paintEvent` (around line 250-300), using `option.rect.adjusted(...)` to reserve room.

### 4.3 Dirty also drives diagnostics and git

`dirty_state_changed` fans out to:

- `DiagnosticStore.mark_dirty(path)` → the store switches to **live-only** diagnostics.
- `GitStatusService.request_scan("editor:dirty_true")` → the explorer marks the file as modified.

---

## 5. Encoding

`CodeEditor.load_from_file` (`code_editor.py:2169-2193`):

```python
for encoding in ("utf-8", "utf-8-sig", None):     # None == platform default
    try:
        with open(file_path, "r", **({"encoding": encoding} if encoding else {})) as f:
            content = f.read()
        break
    except (UnicodeDecodeError, LookupError):
        continue

if content is None:
    with open(file_path, "rb") as f:
        content = f.read().decode("utf-8", errors="replace")
```

| Step | Encoding | Purpose |
|---|---|---|
| 1 | `utf-8` | The normal case. |
| 2 | `utf-8-sig` | Strips a UTF-8 BOM. |
| 3 | `None` (platform default) | `latin-1` on most POSIX locales; handles legacy files. |
| 4 | `utf-8` + `errors="replace"` | Last resort; **never** raises. |

> **Invariant:** loading a file must never raise a decode error. A file that cannot be decoded becomes a `FallBack` tab (`tab_editor.py:495-498`).

### Read-only detection

After loading, the file mode is checked (`code_editor.py:2224-2238`):

```python
write_bits = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
if not (path_obj.stat().st_mode & write_bits):
    self.setReadOnly(True); self._update_readonly_tab_indicator(True)
```

A read-only file gets a lock glyph in the tab and every mutating `EditorAPI` call becomes a no-op (`cut`, `paste`, `delete` all check `isReadOnly()`).

---

## 6. The `EditorAPI` Facade

`editor/Ironica/api.py:13`. A **per-tab** facade over one `CodeEditor`.

```python
class EditorAPI:
    def __init__(self, editor: QsciScintilla) -> None:
        if editor is None:
            raise ValueError("EditorAPI requires a non-None editor instance")
        self._editor = editor

    @property
    def editor(self) -> QsciScintilla:   # escape hatch
        ...
```

- Constructed with the `CodeEditor` (or the `MiniMapHostWidget` — `EditorAPI` resolves the inner widget).
- `EditorContainer.current_editor()` returns `EditorAPI(widget)` **only** when the current tab is a `MiniMapHostWidget`; otherwise `None` (`ui_build.py:87-93`).
- Every mutating method checks `isReadOnly()` first and returns silently if the editor is read-only.

### Operation groups

| Group | Methods |
|---|---|
| Clipboard | `cut`, `copy`, `copy_as_plain_text`, `paste`, `delete`, `select_all`, `select_none` |
| History | `undo`, `redo` |
| Structure | `indent`, `unindent`, `format_code`, `comment_line`, `comment`, `uncomment_line`, `uncomment`, `duplicate_line`, `duplicate_selection` |
| Navigation | `goto_definition`, `goto_declaration`, `goto_implementation`, `goto_usage`, `goto_reference`, `find_usages`, `goto_implementation_file` |
| Folding | `expand_current`, `expand_all`, `collapse_current`, `smart_collapse`, `collapse_includes` |
| File | `load_file`, `save`, `set_language` |

**Rule:** menu commands call `EditorAPI`, never `CodeEditor` directly. `CodeEditor` is the widget; `EditorAPI` is the contract.

---

## 7. Language & Provider Wiring

### 7.1 Resolution

`LanguageRegistry` (`editor/Ironica/language_engine.py:225`) maps a file extension to a language config. `tabs.set_language_for_file(path)` (`tab_editor.py:897`) is the normal entry point; `tabs.set_language(lang)` (`tab_editor.py:890`) is the manual override.

### 7.2 Provider lifetime

The provider is obtained **once at tab creation** (`tab_editor.py:515-532`):

```python
provider = LanguageRegistry.get_provider(language)
if provider.has_diagnostics():
    code_editor._diag_manager = provider.create_diagnostic_manager(...)
if hasattr(provider, "create_completion_manager"):
    code_editor._completion_manager = provider.create_completion_manager(...)
```

Both managers have a `shutdown()` that is called on tab close (`tab_editor.py:728-736`). **A new manager type must also be shut down**, or it leaks threads and keeps the file's diagnostics alive.

### 7.3 Provider cache invalidation

`load_from_file` calls `provider.invalidate_cache()` if the provider has one (`code_editor.py:2197-2201`). This is how a file reload picks up new on-disk content for navigation.

---

## 8. Cursor, Selection & Position

### 8.1 Position tracking

`CodeEditor` emits `position_changed(line, col)` from `_emit_position` (`code_editor.py:1066`). The window connects it to `update_position_status` so the status bar shows `Ln, Col`.

### 8.2 Occurrence highlighting

Selecting an identifier highlights every occurrence in the file:
- `_setup_occurrence_highlight` (937) — installs the indicator
- `_schedule_occurrence_update` (979) — debounced
- `_update_occurrence_highlight` (997) — computes the matches
- `_clear_occurrence_highlight` (985)

The matcher is **byte-offset aware** (lines 1043-1051): it converts character offsets to UTF-8 byte offsets because Scintilla works in bytes. Do not "simplify" this to a plain character count — it breaks on non-ASCII files.

### 8.3 Brace matching

`_setup_brace_highlight` (820) / `_update_brace_highlight` (888) / `_is_complementary_bracket` (931). The matching style is drawn with `SCI_STYLESETBACK` on the current line.

---

## 9. Folding

| Concern | Owner |
|---|---|
| Folding engine | `editor/Ironica/utils/folding.py` → `FoldManager`, `FoldRegion` |
| Scintilla folding setup | `CodeEditor._setup_folding` (724) |
| Fold display text | `_setup_folding_display_text` (731), `_apply_folding_display_colors` (739) |
| Custom fold text | `set_custom_import_fold_text` (753) → `SCI_SETFOLDEXPANDEDTEXT` |
| Recompute trigger | `_schedule_fold_recompute` (344) → `_recompute_folds` (375), 500 ms debounce |
| Provider regions | `provider.get_fold_regions()` / `provider.has_folding()` |

**Import folds** show the full folded text (e.g. `import os, sys, …`) instead of `…`. This is a Scintilla `SCI_SETFOLDEXPANDEDTEXT` feature.

> **Known limitation:** Scintilla style backgrounds cannot be alpha-blended. The "ghost text" effect is achieved by matching the paper colour exactly (`SCI_STYLESETBACK`). See the `FOLD_GHOST_BG` entry in `CHANGELOG.md`. Do not replace this with an alpha colour.

---

## 10. Snippets

- `CodeEditor.load_snippets(path)` (289) reads a JSON snippet file.
- `_extract_snippets(data)` (303) parses it.
- `_expand_snippet(line, col, trigger, content)` (312) performs the expansion.
- Snippet paths are registered per language by `LanguageRegistry.register_snippet_path(lang, path)`.
- The C++ provider sets `slash_snippets_only = True`, so `/` triggers completion there.

---

## 11. Diagnostics Painting on the Editor

The editor receives diagnostics from `ProblemsWidget._paint_editor`:

| Call | Effect |
|---|---|
| `set_diagnostic_ranges(...)` | Squiggly underline under the offending ranges. |
| `set_deemphasized_ranges(...)` | A separate dimmed range set — **not** a second squiggle. |
| `set_diagnostic_labels(...)` | Margin markers / labels. |

The `CodeEditor.diagnostic_ticks_changed(list)` signal (`code_editor.py:33`) reports tick changes back to the Problems panel.

---

## 12. Invariants Summary

1. One `CodeEditor` per text tab; unwrap with `_unwrap_code_editor` / `ensure_inner`.
2. `CodeEditor._is_dirty` is the single dirty flag; the tab marker is a mirror that must be rebuilt after any tab-set change.
3. `EditorAPI` is the only surface menus should use.
4. Loading never raises on encoding; the fallback chain ends in `errors="replace"`.
5. Files without write bits open read-only and every mutating API call becomes a no-op.
6. Every provider-created manager must be shut down on tab close.
7. `provider.invalidate_cache()` must be called on reload so navigation sees fresh content.
8. Position/occurrence math is **byte-based**, not character-based.
9. `add_new_editor` is idempotent per normalised path — do not create duplicate tabs.
10. Any new signal on `CodeEditor` must be disconnected in `close_editor`, or it leaks across tabs.
