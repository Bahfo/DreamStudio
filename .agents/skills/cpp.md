# Skill: C / C++ Contributions

> **Purpose**: house style, build commands, and safety rules for the native parts of DreamStudio.
> **Applies to**: `hex-editor/` (C17 shared library), `DreamCLI/` (C++17 CLI), and any new native helper.

---

## 0. Where Native Code Lives

| Project | Language | Standard | Output | Loaded by |
|---|---|---|---|---|
| `hex-editor/` | C | **C17** | `libinspector.so` → `native/build/lib/` | `editor/Ironica/inspector/binding.py` via `ctypes` |
| `DreamCLI/` | C++ | **C++17** | `dscript` executable, `libdreamcli_lib.a` | standalone CLI |
| `native/` | — | — | holds `build/lib/libinspector.so` | output directory for `hex-editor` |

Both projects are **optional**. The IDE runs without them; only the corresponding feature degrades.

---

## 1. Build & Test

```bash
# native inspector (C17)
cd hex-editor
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)"

# DreamCLI (C++17)
cd DreamCLI
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)"
```

> **Stale cache trap:** the checked-in `build/` folders contain a `CMakeCache.txt` with a different absolute source path. Reconfiguring in place fails. Fix with `rm -rf hex-editor/build DreamCLI/build` first.

> **Output trap:** `hex-editor/CMakeLists.txt` sets `LIBRARY_OUTPUT_DIRECTORY` to `${CMAKE_CURRENT_SOURCE_DIR}/../native/build/lib`, so the `.so` lands in `native/build/lib/`, **not** in `hex-editor/build/`.

### Compiler flags (already set in CMake)

| Project | Flags |
|---|---|
| `hex-editor` | `-fPIC -O2 -Wall -Wextra` |
| `DreamCLI` | `-Wall -Wextra -Wpedantic` |

Both build with **warnings as output, not as errors**. Treat new warnings as failures.

### Smoke test

```bash
# DreamCLI
./DreamCLI/build/dscript --help

# inspector: verify the library exports the expected symbols
nm -D --defined-only native/build/lib/libinspector.so | grep binary_file_
```

### From Python

```python
import ctypes
from editor.utils.resource_path import resource_path

lib = ctypes.CDLL(resource_path("native/build/lib/libinspector.so"))
```

---

## 2. House Style

### 2.1 `hex-editor/` (C)

Follows a **snake_case, Allman-brace, kernel-style** convention:

```c
// (C) COPYRIGHT 2026 Excellent TechStacks - All Rights Reserved.
// <Module> Source Code for DreamStudio ELF Inspection.
// Code is licensed under the GPLv3 License.

#include "inspector.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>


struct BinaryFile {
    FILE *handle;
};


static uint16_t read_u16(
    const unsigned char *data,
    uint8_t elf_data) {

    if (elf_data == 1) {
        return (uint16_t)data[0] |
               ((uint16_t)data[1] << 8);
    }

    return ((uint16_t)data[0] << 8) |
           (uint16_t)data[1];
}
```

Rules:
- **snake_case** for functions, variables, and typedefs.
- **Braces on their own line** (Allman), with a blank line after the opening brace of a function.
- **4-space** indent; continuation lines align under the opening parenthesis.
- `static` for file-local functions; `const` on every pointer that is not modified.
- Explicit casts on every narrowing conversion (`(uint16_t)`, `(uint32_t)`).
- Headers use the include guard style: `#ifndef INSPECTOR_H` / `#define INSPECTOR_H` / `#endif`.
- `extern "C"` guards around the public API so the symbols can be loaded with `ctypes`.

### 2.2 `DreamCLI/` (C++)

Follows a **camelCase-method, trailing-underscore-member** convention:

```cpp
#pragma once

#include <cstddef>
#include <string>
#include <vector>

#include "token.hpp"

class Lexer {
public:
    explicit Lexer(std::string source);
    std::vector<Token> tokenize();

private:
    std::string source_;

    std::size_t position_ = 0;
    std::size_t line_ = 1;
    std::size_t column_ = 1;

    bool isAtEnd() const;
    char peek() const;
    char advance();
    bool match(char expected);
};
```

Rules:
- **Types / classes**: `PascalCase` (`Lexer`, `Token`, `TokenType`).
- **Methods and free functions**: `camelCase` (`tokenize`, `isAtEnd`, `keywordTable`).
- **Member variables**: `snake_case_` with a **trailing underscore** (`source_`, `position_`).
- **Constants**: `kCamelCase` or `UPPER_SNAKE` (be consistent within a file).
- **Enums**: `enum class` with `UPPER_SNAKE` enumerators (`TokenType::END_OF_FILE`).
- **Headers**: `#pragma once`.
- Include order: own header first, then a blank line, then `<std>` headers, then project headers.
- Anonymous namespace for file-local helpers (`namespace { ... }  // namespace`).
- `const` on every method that can be.
- Prefer `std::string` + `std::vector`; avoid raw pointers. When a raw pointer is unavoidable, express ownership in the name (`BinaryFile *file`).

> **Note:** the two native projects use **different** conventions. Do **not** normalise them — match the file you are editing.

---

## 3. Portability Rules

| Rule | Why |
|---|---|
| Never `goto` | — |
| Use `<cstdint>` types (`uint8_t`, `uint32_t`) instead of `char`/`int` for binary data | Signedness bugs |
| Check every `fread`/`fwrite` return value | Silent truncation |
| Free every allocation on every path, including error paths | Leaks in a long-lived IDE process |
| Prefer `size_t` for sizes and indices | Signed/unsigned comparison warnings |
| On Windows, use `fopen_s` / explicit `_WIN32` guards | MSVC does not support `fopen_s` outside the secure API set |
| Keep the public API `extern "C"`-compatible | It is loaded via `ctypes` |

---

## 4. The `ctypes` Contract

`editor/Ironica/inspector/binding.py` loads `libinspector.so`. The Python side declares the signatures explicitly, e.g.:

```python
lib.binary_file_open.argtypes = [ctypes.c_char_p]
lib.binary_file_open.restype = ctypes.c_void_p
```

**Any change to the C signatures must be mirrored in the Python `argtypes`/`restype` declarations**, or you get silent memory corruption instead of an error.

Public C API (`hex-editor/include/inspector.h`):

```c
BinaryFile *binary_file_open(const char *path);
void binary_file_close(BinaryFile *file);
int binary_file_read_elf_header(BinaryFile *file, ElfHeaderInfo *header);
size_t binary_file_get_section_count(const ElfHeaderInfo *header);
int binary_file_read_section(BinaryFile *file, const ElfHeaderInfo *header,
                              uint16_t index, ElfSectionInfo *section);
```

### Rebuild requirement

After changing the C code, **rebuild** and re-copy the `.so`. The PyInstaller spec bundles three copies:

- `native/build/lib/libinspector.so` → `native/build/lib`
- `hex-editor/build/libinspector.so` → `hex-editor/build`
- `hex-editor/build/libbinary_inspector.so` → `hex-editor/build`
- `native/build/lib/libinspector.so` → `editor/Ironica/inspector` (fallback for `binding.py`)

If a new native file is added, add it to `packaging/DreamStudio.spec` → `binaries` **and** to the runtime search list in `binding.py`.

---

## 5. Safety Checklist for Native Changes

- [ ] Rebuilt with `cmake --build` and **no new warnings**.
- [ ] Public C signatures unchanged, or the Python `ctypes` declarations updated in the same commit.
- [ ] Every allocation freed on every path.
- [ ] `extern "C"` guards still wrap the public API.
- [ ] The `.so` was copied to every location the runtime searches.
- [ ] `packaging/DreamStudio.spec` updated if a new native artefact is introduced.
- [ ] The IDE still starts when the library is **absent** (the feature degrades, the IDE does not crash).
- [ ] A Python-side test covers the behaviour (`tests/test_*`).

---

## 6. Adding a New Native Component

1. Create `my_component/` with a `CMakeLists.txt` (mirror `hex-editor/CMakeLists.txt`).
2. Put public headers in `include/` with an include guard and `extern "C"`.
3. Put the implementation in `src/`.
4. Build to a dedicated output directory; **do not** write into another project's build dir.
5. Add the artefact to `packaging/DreamStudio.spec` → `binaries`.
6. Load it from Python with `ctypes`, declaring every `argtypes`/`restype`, and wrap the load in `try/except` so a missing library degrades the feature.
7. Document the new component in `.agents/context/dependencies.md` §9.
