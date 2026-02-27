import os
import tkinter as tk
import threading
from pygments import lex
from pygments.lexers import get_lexer_by_name, get_lexer_for_filename, guess_lexer
from pygments.lexers.special import TextLexer


class Highlighter:
    """
    Syntax highlighter:
    - Lexes the full document in a background thread (correct tokens always)
    - Caches a line→char_offset map so viewport math is O(1), not O(doc)
    - Applies tags only to the visible viewport (fast UI updates)
    - Separate fast path for scroll (no re-lex, no full-doc read)
    """

    BUFFER_LINES = 20

    def __init__(self, master, language="", *args, **kwargs):
        self.text     = master
        self.base     = master.base
        self.language = language

        self._debounce_id   = None
        self._thread_lock   = threading.Lock()
        self._active_thread = None

        # Token cache built by background thread
        # Each entry: (tag_name, abs_char_offset, length)
        self._token_cache      = []
        self._token_cache_hash = None

        # Line offset cache: list where index i = char offset of line (i+1)
        # e.g. _line_offsets[0] = 0 means line 1 starts at char 0
        # Built alongside the token cache in the background thread.
        self._line_offsets      = []   # [char_offset_of_line_1, char_offset_of_line_2, ...]
        self._line_offsets_hash = None

        self.lexer = self._resolve_lexer(language, master)

        self.valid_tags = set()
        self._tag_map   = {}
        self._setup_tags()

        # Proxy yview for scroll highlighting
        self._orig_yview = master.yview
        master.yview     = self._proxy_yview

    # -------------------------------------------------------------------------
    # Lexer resolution
    # -------------------------------------------------------------------------

    def _resolve_lexer(self, language, master):
        if language:
            try:
                return get_lexer_by_name(language)
            except Exception:
                pass
        path = getattr(master, "path", "") or ""
        if path:
            try:
                return get_lexer_for_filename(
                    os.path.basename(path),
                    encoding=getattr(master, "encoding", "utf-8"),
                )
            except Exception:
                pass
        try:
            sample = master.get("1.0", "100.0")
            if sample.strip():
                return guess_lexer(sample)
        except Exception:
            pass
        return TextLexer()

    def update_lexer(self, language="", path=""):
        self.lexer = self._resolve_lexer(language or self.language, self.text)
        self._token_cache_hash = None
        self.schedule_highlight()

    # -------------------------------------------------------------------------
    # Tag setup
    # -------------------------------------------------------------------------

    def _setup_tags(self):
        for key, color in self.base.settings.syntax.items():
            clean = key
            for prefix in ("Token.", "token."):
                if clean.startswith(prefix):
                    clean = clean[len(prefix):]
                    break
            tag = f"syn.{clean}"
            self.text.tag_configure(tag, foreground=color)
            self.valid_tags.add(tag)
            self._tag_map[clean] = tag

    def _token_to_tag(self, token_type):
        parts = str(token_type).split(".")
        for i in range(len(parts), 1, -1):
            key = ".".join(parts[1:i])
            if key in self._tag_map:
                return self._tag_map[key]
        return None

    # -------------------------------------------------------------------------
    # Entry points
    # -------------------------------------------------------------------------

    def _proxy_yview(self, *args):
        result = self._orig_yview(*args)
        self._schedule_apply_only()
        return result

    def schedule_highlight(self, event=None):
        """Called on keypress — debounced, triggers re-lex if content changed."""
        if self._debounce_id:
            self.text.after_cancel(self._debounce_id)
        self._debounce_id = self.text.after(80, self._collect_and_dispatch)

    def _schedule_apply_only(self):
        """Called on scroll — just re-applies cached tokens, no re-lex."""
        if self._debounce_id:
            self.text.after_cancel(self._debounce_id)
        self._debounce_id = self.text.after(16, self._apply_cache_to_viewport)

    # -------------------------------------------------------------------------
    # Step 1 — main thread: hash check, spawn thread if needed
    # -------------------------------------------------------------------------

    def _collect_and_dispatch(self):
        self._debounce_id = None

        if isinstance(self.lexer, TextLexer):
            return

        try:
            full_content = self.text.get("1.0", "end-1c")
        except tk.TclError:
            return

        content_hash = hash(full_content)

        if content_hash == self._token_cache_hash:
            self._apply_cache_to_viewport()
            return

        with self._thread_lock:
            if self._active_thread and self._active_thread.is_alive():
                return

            self._active_thread = threading.Thread(
                target=self._lex_full_document,
                args=(full_content, content_hash),
                daemon=True,
            )
            self._active_thread.start()

    # -------------------------------------------------------------------------
    # Step 2 — background thread: lex + build line offset map
    # -------------------------------------------------------------------------

    def _lex_full_document(self, full_content, content_hash):
        try:
            # Build line offset map: _line_offsets[i] = char offset where
            # line (i+1) starts.  O(n) once, then O(1) lookups forever.
            line_offsets = [0]
            for i, ch in enumerate(full_content):
                if ch == "\n":
                    line_offsets.append(i + 1)
            # line_offsets[0] = start of line 1
            # line_offsets[k] = start of line (k+1)

            tokens_out  = []
            char_offset = 0
            for token_type, value in lex(full_content, self.lexer):
                t_len = len(value)
                tag   = self._token_to_tag(token_type)
                if tag and value.strip():
                    tokens_out.append((tag, char_offset, t_len))
                char_offset += t_len

            self.text.after(
                0,
                lambda c=tokens_out, lo=line_offsets, h=content_hash:
                    self._store_and_apply(c, lo, h),
            )
        except Exception as exc:
            print(f"[Highlighter] lex error: {exc}")

    # -------------------------------------------------------------------------
    # Step 3 — main thread: store cache and apply to viewport
    # -------------------------------------------------------------------------

    def _store_and_apply(self, token_cache, line_offsets, content_hash):
        self._token_cache      = token_cache
        self._line_offsets     = line_offsets
        self._token_cache_hash = content_hash
        self._apply_cache_to_viewport()

    def _apply_cache_to_viewport(self):
        """
        Apply cached tokens to the visible viewport only.
        Uses the pre-built line offset map — no full-doc reads here.
        """
        if not self._token_cache or not self._line_offsets:
            return

        try:
            if not self.text.winfo_exists():
                return

            widget_height = self.text.winfo_height()
            total_lines   = len(self._line_offsets)

            vis_top    = int(self.text.index("@0,0").split(".")[0])
            vis_bottom = int(self.text.index(f"@0,{widget_height}").split(".")[0])

            start_line = max(1, vis_top - self.BUFFER_LINES)
            end_line   = min(total_lines, vis_bottom + self.BUFFER_LINES)

            tk_start = f"{start_line}.0"
            tk_end   = f"{end_line}.end"

            # O(1) lookup using cached line offsets (no string splitting/reading)
            slice_start_c = self._line_offsets[start_line - 1]

            if end_line < len(self._line_offsets):
                # end of end_line = start of next line - 1
                slice_end_c = self._line_offsets[end_line] - 1
            else:
                # last line: use total content length
                slice_end_c = self._line_offsets[-1] + len(
                    self.text.get(f"{total_lines}.0", f"{total_lines}.end")
                )

            # Clear old tags in viewport only
            for tag in self.valid_tags:
                self.text.tag_remove(tag, tk_start, tk_end)

            # Apply tokens overlapping the viewport
            for tag, abs_off, t_len in self._token_cache:
                tok_end = abs_off + t_len
                if tok_end <= slice_start_c or abs_off >= slice_end_c:
                    continue
                self.text.tag_add(tag, f"1.0 + {abs_off}c", f"1.0 + {tok_end}c")

        except (tk.TclError, RuntimeError, ValueError):
            pass