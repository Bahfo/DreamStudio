"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Hex dump rendering for binary / ELF inspection.

Produces a deterministic, readable hex+ASCII representation for display
inside the read-only code editor.
"""

from __future__ import annotations

import os
import pathlib


def generate_hex_dump(
    file_path: str,
    max_bytes: int = 512 * 1024,
    bytes_per_line: int = 16,
) -> str:
    """Render *file_path* as a hex dump.

    Args:
        file_path: Absolute path to the binary file.
        max_bytes: Maximum bytes to render (prevents huge files from
            freezing the UI). Remaining bytes are truncated with a note.
        bytes_per_line: Number of bytes per line (16 is conventional).

    Returns:
        A string suitable for ``CodeEditor.setText()`` containing offset,
        hex bytes, and ASCII representation.
    """
    path = pathlib.Path(file_path)
    try:
        size = path.stat().st_size
    except OSError:
        return f"; Unable to stat file: {file_path}\n"

    try:
        with open(file_path, "rb") as f:
            data = f.read(max_bytes)
    except OSError as exc:
        return f"; Failed to read binary file: {exc}\n"

    truncated = size > len(data)
    lines: list[str] = []
    lines.append(f"; Binary file: {path.name}  ({size} bytes)")
    lines.append(f"; Showing {len(data)} bytes as hex dump")
    lines.append(f"; Offset     Hex bytes                               ASCII")
    lines.append(f"; {'-'*8}  {'-'*47}  {'-'*16}")

    for offset in range(0, len(data), bytes_per_line):
        chunk = data[offset : offset + bytes_per_line]
        hex_parts: list[str] = []
        ascii_parts: list[str] = []
        for b in chunk:
            hex_parts.append(f"{b:02X}")
            if 32 <= b <= 126:
                ascii_parts.append(chr(b))
            else:
                ascii_parts.append(".")
        # Pad hex area when last line is short
        hex_str = " ".join(hex_parts)
        # Align hex column to fixed width (16*3 -1 =47)
        pad_len = bytes_per_line * 3 - 1
        hex_str = hex_str.ljust(pad_len)
        ascii_str = "".join(ascii_parts)
        lines.append(f"{offset:08X}  {hex_str}  {ascii_str}")

    if truncated:
        lines.append("")
        lines.append(f"; ... truncated ({size - len(data)} more bytes not shown)")
        lines.append(f"; Full file size: {size} bytes")

    return "\n".join(lines) + "\n"


def is_elf_file(file_path: str) -> bool:
    """Fast ELF magic check without invoking native code.

    Returns ``True`` for ELF64 files (class byte == 2). This mirrors the
    C inspector's minimum requirement (recognize ELF64).
    """
    try:
        with open(file_path, "rb") as f:
            header = f.read(5)
            if len(header) < 5:
                return False
            if header[0] != 0x7F or header[1:4] != b"ELF":
                return False
            elf_class = header[4]
            return elf_class == 2
    except OSError:
        return False
