# Known Issues

## C++ precompiled header (PCH) build failures

The C++ plugin builds a precompiled header (`.ds/cpp/stable.pch`) in the
background to speed up cold translation-unit parses. The PCH is strictly
additive: every failure below falls back to parsing without it, so
completion keeps working at unaccelerated speed.

Recorded failure modes:

1. **Missing serializer in the bindings.** If the installed libclang
   Python bindings lack `TranslationUnit.save`, the build is skipped.
   (Verified present in the pinned `libclang==18.1.1`.)
2. **Stub header fails to parse.** Conflicting third-party headers, exotic
   pragmas, or headers requiring generated config macros abort the build.
   Logged once; completion proceeds without a PCH.
3. **Resource exhaustion.** Enormous header sets (out-of-memory during
   serialization) or a full/read-only disk abort the build. Logged once.
4. **Empty candidate set.** A project with no `#include`s to harvest
   skips the build as a no-op; no file is written.
5. **Flag/header drift is not a failure.** A `stable.pch.key` mismatch
   (changed flags, headers, or mtimes) only means the PCH is not used
   while the background worker rebuilds it. Typing is never blocked.
