# C++ Completion Timing Notes — dummy project `/tmp/dummyproj`

Machine: i7-1255U (12 threads), 15 GB RAM, libclang 18.1.1 (pip).
Project: 7 files, each using one OS library; `CMakeLists.txt` with explicit
sources, `find_package(SDL2/OpenSSL)`, `include_directories(include)`.
No `compile_commands.json`, no `.ds` marker unless noted — i.e. the
"imported project" path. Timings are single-run wall clock.

## Per-library cold completion (`engine.complete`, fresh engine each row)

| File (trigger) | Cold parse | Rounds | codeComplete | Shape | Cold total | Warm total | Rows | Hit |
|---|---|---|---|---|---|---|---|---|
| main_sdl (`SDL_Tex`) | fast-fail | app.hpp→SDL.h | ~0.4 | 0.19 | 1.58s | 0.71s | 19 | SDL_Texture ✓ |
| zip_zlib (`crc`) | fast-fail | app.hpp | ~0.0 | 0.03 | 0.07s | 0.03s | 7 | crc32 ✓ |
| audio_alsa (`snd_pcm_hw_params_m`) | fast-fail | app.jsx→∅ | ~0.0 | 0.07 | 0.17s | 0.12s | 1 | ✓ |
| draw_cairo (`cairo_set_source_rg`) | fast-fail | app.hpp | ~0.0 | 0.02 | 0.07s | 0.04s | 2 | rgb/rgba ✓ |
| tls_openssl (`TLS_m`) | 0.34s | app.hpp→ssl.h | ~0.1 | 0.22 | 0.48s | 0.38s | 19 | TLS_method ✓ |
| math_eigen (`transposeInPla`, member `.`) | fast-fail | app.hpp→Eigen/Dense | **1.74s** | 0.01 | 4.54s | **2.00s** | 1 | ✓ |
| ui_qt (`setApplicationNa`, member `.`) | fast-fail | app.hpp→**QApplication unresolvable** | — | — | 0.11s | 0.00s | 0 | ✗ |

## Findings

1. **Implicit headers are free.** `zlib.h`, `asoundlib.h`, `<cairo/cairo.h>`
   resolve via clang's built-in `/usr/include` — no flags, no cost.
2. **One-level project headers resolve via tree walk.** `app.hpp`
   (in `include/`, no DB entry) found by bounded project search every time.
3. **System subdir headers resolve via 1-level scan.** `SDL.h` →
   `-I/usr/include/SDL2`, `ssl.h` → `-I/usr/include/openssl`,
   `Eigen/Dense` → `-I/usr/include/eigen3`. Zero hardcoded names involved.
4. **Missing headers chain.** Round N's parse reveals round N+1's missing
   header (`app.hpp` → `SDL.h`). The retry loop converges (bounded at 4);
   each round is a full re-parse, so cold totals stack parses.
5. **Qt is the documented limit.** `QApplication` lives at
   `qt6/QtWidgets/QApplication` (depth 2); the resolver searches one
   subdir level only → unresolvable → 0 rows, fast. Deeper layouts need a
   deeper (bounded) search.
6. **Eigen dominates via `codeComplete`, not parsing.** Warm query =
   1.74s `codeComplete` + 0.01s shaping on a template-heavy TU. Shaping
   cost tracks *total* rows walked, not matches (0.19–0.22s at ~4000
   rows, 0.01–0.07s below ~2000).
7. **Macro split (SDL TU):** macros+brief = 4002 rows / 0.16s,
   no-macros = 2119 rows / 0.10s. Basis for the adaptive-macro heuristic.
8. **Warm queries reuse everything.** Second identical call: TU cache hit
   (flags tuple includes resolved extras), no re-parse, no re-resolve.
   Cost EMA tracks it (SDL 463ms, Eigen 1585ms, zlib 15ms) for the
   cost-scaled debounce.
9. **PCH (5.4 MB for this project, 0.6–0.8s build):** parse with valid PCH
   0.5s → 0.2s on the small TU; Eigen full parse 5.0s → 4.2s. Caveat
   found while measuring: the PCH stub is built with base flags only, so
   headers discovered *later* by the resolver (e.g. Eigen) are NOT in the
   PCH — the PCH never covers them until a rebuild with wider flags.
   Key validation (flags-hash + includes + header mtime) works; a bogus
   PCH path is correctly rejected with a hard parse error.
10. **Member completions (`.`) cost the same as free identifiers** once
    the TU is warm — no separate member penalty observed (Eigen member
    cost is template instantiation inside `codeComplete`, not the `.`).

## Biggest levers, in measurement order

1. Fewer cold parses (PCH validity + flag stability) — parses are the
   only multi-second stage outside Eigen-scale `codeComplete`.
2. Smaller `codeComplete` input (adaptive macros: −47% rows on SDL).
3. `codeComplete` on template-heavy TUs (Eigen 1.74s warm) has no cheap
   fix at this layer — candidate: slim-query flags / idle pre-query.
