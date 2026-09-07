"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Python ctypes wrapper around the native ELF inspector shared library.

This module is the single place where raw ``ctypes`` calls live.
All higher-level code must use :class:`Inspector` instead of touching
``ctypes`` directly.
"""

from __future__ import annotations

import ctypes
import pathlib
from dataclasses import dataclass
from typing import List, Optional, Tuple

logger = __import__("logging").getLogger(__name__)


# ----------------------------------------------------------------------
# Structures — must match C exactly (see hex-editor/include/inspector.h)
# ----------------------------------------------------------------------


class ElfHeaderInfo(ctypes.Structure):
    """Mirror of C ``ElfHeaderInfo``.

    Fields are in the exact same order and use compatible C types.
    Padding is handled by ``ctypes`` natural alignment (no ``_pack_``),
    which matches the C compiler's layout on x86-64 (verified size 40).
    """

    _fields_ = [
        ("elf_class", ctypes.c_uint8),
        ("elf_data", ctypes.c_uint8),
        ("type", ctypes.c_uint16),
        ("machine", ctypes.c_uint16),
        ("entry", ctypes.c_uint64),
        ("program_header_offset", ctypes.c_uint64),
        ("section_header_offset", ctypes.c_uint64),
        ("program_header_count", ctypes.c_uint16),
        ("section_header_count", ctypes.c_uint16),
        ("section_name_string_table_index", ctypes.c_uint16),
    ]


class ElfSectionInfo(ctypes.Structure):
    """Mirror of C ``ElfSectionInfo`` (size 40 on x86-64)."""

    _fields_ = [
        ("name_offset", ctypes.c_uint32),
        ("type", ctypes.c_uint32),
        ("address", ctypes.c_uint64),
        ("offset", ctypes.c_uint64),
        ("size", ctypes.c_uint64),
        ("flags", ctypes.c_uint64),
    ]


# ----------------------------------------------------------------------
# Helpers to locate the shared library without hardcoding absolute paths
# ----------------------------------------------------------------------


def _find_library() -> pathlib.Path:
    """Locate ``libinspector.so`` relative to the project/package.

    Searches a small set of predictable locations relative to this file
    and the project root. No absolute hard-coded paths are used.
    """
    this = pathlib.Path(__file__).resolve()
    # project root is three levels up from editor/Ironica/inspector/
    try:
        project_root = this.parents[3]
    except IndexError:
        project_root = this.parent

    candidates: List[pathlib.Path] = [
        project_root / "native" / "build" / "lib" / "libinspector.so",
        project_root / "hex-editor" / "build" / "libinspector.so",
        project_root / "hex-editor" / "build" / "libbinary_inspector.so",
        this.parent / "libinspector.so",
        pathlib.Path.cwd() / "native" / "build" / "lib" / "libinspector.so",
        pathlib.Path.cwd() / "hex-editor" / "build" / "libinspector.so",
    ]
    for cand in candidates:
        if cand.is_file():
            return cand
    # Last resort: rely on system loader search
    raise FileNotFoundError(
        "Could not locate libinspector.so. Searched: "
        + ", ".join(str(c) for c in candidates)
    )


def _load_lib() -> ctypes.CDLL:
    path = _find_library()
    try:
        lib = ctypes.CDLL(str(path))
        logger.debug("Loaded inspector library from %s", path)
        return lib
    except OSError as exc:
        raise OSError(f"Failed to load inspector library {path}: {exc}") from exc


# ----------------------------------------------------------------------
# Python-friendly dataclasses
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class ElfHeader:
    """Python representation of ELF header fields."""

    elf_class: int
    elf_data: int
    type: int
    machine: int
    entry: int
    program_header_offset: int
    section_header_offset: int
    program_header_count: int
    section_header_count: int
    section_name_string_table_index: int

    # Derived human-readable names (filled by Inspector helper)
    class_name: str = ""
    data_name: str = ""
    type_name: str = ""
    machine_name: str = ""


@dataclass(frozen=True)
class ElfSection:
    """Python representation of ELF section entry."""

    index: int
    name: str
    name_offset: int
    type: int
    type_name: str
    address: int
    offset: int
    size: int
    flags: int
    flags_name: str


# ----------------------------------------------------------------------
# Main wrapper
# ----------------------------------------------------------------------


class Inspector:
    """Single abstraction over the native ELF inspector.

    Handles library loading, argtypes/restype declarations, handle
    management, and conversion of C results to Python values.
    """

    def __init__(self) -> None:
        self._lib = _load_lib()
        self._configure()

    def _configure(self) -> None:
        lib = self._lib
        # Opaque BinaryFile* -> c_void_p
        lib.binary_file_open.argtypes = [ctypes.c_char_p]
        lib.binary_file_open.restype = ctypes.c_void_p

        lib.binary_file_close.argtypes = [ctypes.c_void_p]
        lib.binary_file_close.restype = None

        lib.binary_file_read_elf_header.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ElfHeaderInfo),
        ]
        lib.binary_file_read_elf_header.restype = ctypes.c_int

        lib.binary_file_get_section_count.argtypes = [ctypes.POINTER(ElfHeaderInfo)]
        lib.binary_file_get_section_count.restype = ctypes.c_size_t

        lib.binary_file_read_section.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ElfHeaderInfo),
            ctypes.c_uint16,
            ctypes.POINTER(ElfSectionInfo),
        ]
        lib.binary_file_read_section.restype = ctypes.c_int

        # Returns malloc'd char* — use void_p to avoid auto conversion
        lib.binary_file_read_section_name.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ElfHeaderInfo),
            ctypes.POINTER(ElfSectionInfo),
        ]
        lib.binary_file_read_section_name.restype = ctypes.c_void_p

        lib.elf_class_name.argtypes = [ctypes.c_uint8]
        lib.elf_class_name.restype = ctypes.c_char_p

        lib.elf_data_name.argtypes = [ctypes.c_uint8]
        lib.elf_data_name.restype = ctypes.c_char_p

        lib.elf_machine_name.argtypes = [ctypes.c_uint16]
        lib.elf_machine_name.restype = ctypes.c_char_p

        lib.elf_type_name.argtypes = [ctypes.c_uint16]
        lib.elf_type_name.restype = ctypes.c_char_p

        lib.elf_section_type_name.argtypes = [ctypes.c_uint32]
        lib.elf_section_type_name.restype = ctypes.c_char_p

        lib.elf_section_flags_name.argtypes = [ctypes.c_uint64]
        lib.elf_section_flags_name.restype = ctypes.c_char_p

        lib.inspector_version.argtypes = []
        lib.inspector_version.restype = ctypes.c_char_p

        lib.inspector_free.argtypes = [ctypes.c_void_p]
        lib.inspector_free.restype = None

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _decode(c_bytes: Optional[bytes]) -> str:
        if c_bytes is None:
            return "Unknown"
        try:
            return c_bytes.decode("utf-8", errors="replace")
        except Exception:
            return str(c_bytes)

    def version(self) -> str:
        """Return inspector version string."""
        val = self._lib.inspector_version()
        return self._decode(val)

    def elf_class_name(self, elf_class: int) -> str:
        return self._decode(self._lib.elf_class_name(elf_class))

    def elf_data_name(self, elf_data: int) -> str:
        return self._decode(self._lib.elf_data_name(elf_data))

    def elf_machine_name(self, machine: int) -> str:
        return self._decode(self._lib.elf_machine_name(machine))

    def elf_type_name(self, etype: int) -> str:
        return self._decode(self._lib.elf_type_name(etype))

    def elf_section_type_name(self, stype: int) -> str:
        return self._decode(self._lib.elf_section_type_name(stype))

    def elf_section_flags_name(self, flags: int) -> str:
        return self._decode(self._lib.elf_section_flags_name(flags))

    # ------------------------------------------------------------------
    # File handling
    # ------------------------------------------------------------------

    def open(self, path: str) -> ctypes.c_void_p:
        """Open binary file, returning opaque handle or None on failure."""
        if not path:
            return None
        bpath = path.encode("utf-8")
        handle = self._lib.binary_file_open(bpath)
        return handle if handle else None

    def close(self, handle: ctypes.c_void_p) -> None:
        """Safely close native file handle."""
        if handle:
            try:
                self._lib.binary_file_close(handle)
            except Exception as exc:
                logger.debug("binary_file_close failed: %s", exc)

    def read_header(self, handle: ctypes.c_void_p) -> Optional[ElfHeader]:
        """Read ELF header via native code.

        Args:
            handle: Opaque file handle from :meth:`open`.

        Returns:
            :class:`ElfHeader` on success, ``None`` on failure.
        """
        if not handle:
            return None
        raw = ElfHeaderInfo()
        rc = self._lib.binary_file_read_elf_header(handle, ctypes.byref(raw))
        if rc != 1:
            return None
        return ElfHeader(
            elf_class=int(raw.elf_class),
            elf_data=int(raw.elf_data),
            type=int(raw.type),
            machine=int(raw.machine),
            entry=int(raw.entry),
            program_header_offset=int(raw.program_header_offset),
            section_header_offset=int(raw.section_header_offset),
            program_header_count=int(raw.program_header_count),
            section_header_count=int(raw.section_header_count),
            section_name_string_table_index=int(raw.section_name_string_table_index),
            class_name=self.elf_class_name(int(raw.elf_class)),
            data_name=self.elf_data_name(int(raw.elf_data)),
            type_name=self.elf_type_name(int(raw.type)),
            machine_name=self.elf_machine_name(int(raw.machine)),
        )

    def read_sections(
        self, handle: ctypes.c_void_p, header: ElfHeader
    ) -> List[ElfSection]:
        """Read all sections for *header*.

        Handles memory ownership for section names via ``inspector_free``.
        """
        if not handle or header is None:
            return []
        # Reconstruct raw header for the C calls (need pointer)
        raw_header = ElfHeaderInfo(
            elf_class=header.elf_class,
            elf_data=header.elf_data,
            type=header.type,
            machine=header.machine,
            entry=header.entry,
            program_header_offset=header.program_header_offset,
            section_header_offset=header.section_header_offset,
            program_header_count=header.program_header_count,
            section_header_count=header.section_header_count,
            section_name_string_table_index=header.section_name_string_table_index,
        )
        count = int(self._lib.binary_file_get_section_count(ctypes.byref(raw_header)))
        sections: List[ElfSection] = []
        for idx in range(count):
            raw_sec = ElfSectionInfo()
            rc = self._lib.binary_file_read_section(
                handle, ctypes.byref(raw_header), idx, ctypes.byref(raw_sec)
            )
            if rc != 1:
                continue
            # Section name — malloc'd, must free
            name_ptr = self._lib.binary_file_read_section_name(
                handle, ctypes.byref(raw_header), ctypes.byref(raw_sec)
            )
            name = ""
            if name_ptr:
                try:
                    name = ctypes.string_at(name_ptr).decode("utf-8", errors="replace")
                except Exception:
                    name = ""
                try:
                    self._lib.inspector_free(name_ptr)
                except Exception:
                    pass
            sections.append(
                ElfSection(
                    index=idx,
                    name=name,
                    name_offset=int(raw_sec.name_offset),
                    type=int(raw_sec.type),
                    type_name=self.elf_section_type_name(int(raw_sec.type)),
                    address=int(raw_sec.address),
                    offset=int(raw_sec.offset),
                    size=int(raw_sec.size),
                    flags=int(raw_sec.flags),
                    flags_name=self.elf_section_flags_name(int(raw_sec.flags)),
                )
            )
        return sections

    def inspect(self, path: str) -> Tuple[Optional[ElfHeader], List[ElfSection], str]:
        """High-level helper: open, read header+sections, close.

        Returns:
            (header_or_None, sections_list, error_message)
            On success error_message is "".
        """
        handle = None
        try:
            handle = self.open(path)
            if not handle:
                return None, [], f"Cannot open file: {path}"
            hdr = self.read_header(handle)
            if hdr is None:
                return None, [], "Not an ELF file or malformed header"
            secs = self.read_sections(handle, hdr)
            return hdr, secs, ""
        except Exception as exc:
            logger.debug("inspect failed for %s: %s", path, exc)
            return None, [], str(exc)
        finally:
            if handle:
                self.close(handle)

    def is_elf(self, path: str) -> bool:
        """Quick ELF magic check without full parsing.

        First checks ELF magic bytes, then confirms via native parser.
        Returns ``True`` only for valid ELF64 files.
        """
        try:
            with open(path, "rb") as f:
                magic = f.read(4)
                if magic != b"\x7fELF":
                    return False
        except Exception:
            return False
        hdr, _, err = self.inspect(path)
        return hdr is not None and err == ""


# Singleton helper
_singleton: Optional[Inspector] = None


def get_inspector() -> Inspector:
    """Return process-wide singleton :class:`Inspector`."""
    global _singleton
    if _singleton is None:
        _singleton = Inspector()
    return _singleton
