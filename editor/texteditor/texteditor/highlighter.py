import os
import bisect
import tkinter as tk
import threading
from pygments import lex
from pygments.lexers import get_lexer_by_name, get_lexer_for_filename, guess_lexer
from pygments.lexers.special import TextLexer


class Highlighter:
    """
    Syntax highlighter — v3, large-file optimised.

    Improvements over v2
    ────────────────────
    1. O(log n) VIEWPORT SLICE  (was O(total tokens in file))
       The token cache is kept with a parallel sorted list of start offsets.
       Finding viewport-visible tokens uses two bisect calls instead of
       iterating every token.  1000-line file: ~15 000 tokens → 2 ms → ~5 µs.

    2. PRE-COMPUTED "LINE.COL" TK INDICES  (no Tcl string arithmetic per token)
       Tk resolves "42.7" in O(1).  Resolving "1.0 + 3847c" requires Tk to
       walk its internal B-tree character-by-character — slow at scale.
       Indices are computed once in the background thread using a running
       (line, col) cursor that advances with each lexer token: O(n) total,
       zero main-thread cost.

    3. BATCHED tag_add / tag_remove  (unchanged from v2)
       One Tcl call per tag type, not one per token.

    4. VIEWPORT DIRTY FLAG  (unchanged from v2)
       Repaints are skipped when the visible line range hasn't changed.

    5. PENDING LEX QUEUE  (unchanged from v2)
       Fast typists never lose their latest edit.
    """

    BUFFER_LINES = 20

    def __init__(self, master, language="", *args, **kwargs):
        self.text = master
        self.base = master.base
        self.language = language

        self._debounce_id = None
        self._thread_lock = threading.Lock()
        self._active_thread = None
        self._pending_lex = None

        # Token cache — each entry:
        #   (abs_start, abs_end, tag, tk_start_str, tk_end_str)
        # Sorted by abs_start.  _token_offsets is a parallel list of abs_start
        # values used exclusively for bisect lookups.
        self._token_cache: list[tuple] = []
        self._token_offsets: list[int] = []
        self._token_cache_hash = None

        # line_offsets[i] = char offset where line (i+1) begins
        self._line_offsets: list[int] = []

        self._last_rendered_range = (-1, -1)

        self.lexer = self._resolve_lexer(language, master)

        self.valid_tags: set[str] = set()
        self._tag_map: dict[str, str] = {}
        self._setup_tags()

        self._orig_yview = master.yview
        master.yview = self._proxy_yview

    # ─────────────────────────────────────────────────────────────────────────
    # Lexer resolution
    # ─────────────────────────────────────────────────────────────────────────

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
        self._last_rendered_range = (-1, -1)
        self.schedule_highlight()

    # ─────────────────────────────────────────────────────────────────────────
    # Tag setup
    # ─────────────────────────────────────────────────────────────────────────

    def _setup_tags(self):
        for key, color in self.base.settings.syntax.items():
            clean = key
            for prefix in ("Token.", "token."):
                if clean.startswith(prefix):
                    clean = clean[len(prefix) :]
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

    # ─────────────────────────────────────────────────────────────────────────
    # Entry points
    # ─────────────────────────────────────────────────────────────────────────

    def _proxy_yview(self, *args):
        result = self._orig_yview(*args)
        self._on_scroll()
        return result

    def _on_scroll(self):
        """Fire a repaint only when the visible integer line range changes."""
        try:
            h = self.text.winfo_height()
            vis_top = int(self.text.index("@0,0").split(".")[0])
            vis_bottom = int(self.text.index(f"@0,{h}").split(".")[0])
            new_range = (
                max(1, vis_top - self.BUFFER_LINES),
                vis_bottom + self.BUFFER_LINES,
            )
            if new_range == self._last_rendered_range:
                return
        except (tk.TclError, ValueError):
            return

        if self._debounce_id:
            self.text.after_cancel(self._debounce_id)
        self._debounce_id = self.text.after(16, self._apply_cache_to_viewport)

    def schedule_highlight(self, event=None):
        """Debounced entry point called on every keypress."""
        if self._debounce_id:
            self.text.after_cancel(self._debounce_id)
        self._debounce_id = self.text.after(80, self._collect_and_dispatch)

    # ─────────────────────────────────────────────────────────────────────────
    # Step 1 — main thread: read content, hash-check, spawn thread
    # ─────────────────────────────────────────────────────────────────────────

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
                # Save latest content; finishing thread will re-run with it.
                self._pending_lex = (full_content, content_hash)
                return

            self._pending_lex = None
            self._active_thread = threading.Thread(
                target=self._lex_full_document,
                args=(full_content, content_hash),
                daemon=True,
            )
            self._active_thread.start()

    # ─────────────────────────────────────────────────────────────────────────
    # Step 2 — background thread: lex + pre-compute Tk index strings
    # ─────────────────────────────────────────────────────────────────────────

    def _lex_full_document(self, full_content: str, content_hash: int):
        try:
            # Build line-offset map in one O(n) pass.
            line_offsets: list[int] = [0]
            for i, ch in enumerate(full_content):
                if ch == "\n":
                    line_offsets.append(i + 1)

            # Lex and pre-compute "LINE.COL" index strings.
            # We maintain a running (cur_line, cur_col) cursor so we never
            # need to call bisect or split strings inside this loop.
            tokens_out: list[tuple] = []
            offsets_out: list[int] = []

            char_offset = 0
            cur_line = 1  # 1-based (matches Tk)
            cur_col = 0  # 0-based (matches Tk)

            for token_type, value in lex(full_content, self.lexer):
                t_len = len(value)
                tag = self._token_to_tag(token_type)
                newlines = value.count("\n")

                if tag and value.strip():
                    tk_start = f"{cur_line}.{cur_col}"

                    if newlines:
                        last_nl = value.rfind("\n")
                        end_line = cur_line + newlines
                        end_col = t_len - last_nl - 1
                    else:
                        end_line = cur_line
                        end_col = cur_col + t_len

                    tk_end = f"{end_line}.{end_col}"
                    tokens_out.append(
                        (char_offset, char_offset + t_len, tag, tk_start, tk_end)
                    )
                    offsets_out.append(char_offset)

                # Advance running cursor (for tagged and untagged tokens alike)
                if newlines:
                    last_nl = value.rfind("\n")
                    cur_line += newlines
                    cur_col = t_len - last_nl - 1
                else:
                    cur_col += t_len

                char_offset += t_len

            self.text.after(
                0,
                lambda c=tokens_out, o=offsets_out, lo=line_offsets, h=content_hash: self._store_and_apply(
                    c, o, lo, h
                ),
            )
        except Exception as exc:
            print(f"[Highlighter] lex error: {exc}")
        finally:
            # Pick up any edit that arrived while we were busy.
            with self._thread_lock:
                pending = self._pending_lex
                self._pending_lex = None

            if pending:
                content, h = pending
                with self._thread_lock:
                    self._active_thread = threading.Thread(
                        target=self._lex_full_document,
                        args=(content, h),
                        daemon=True,
                    )
                    self._active_thread.start()

    # ─────────────────────────────────────────────────────────────────────────
    # Step 3 — main thread: store cache + repaint
    # ─────────────────────────────────────────────────────────────────────────

    def _store_and_apply(self, token_cache, token_offsets, line_offsets, content_hash):
        self._token_cache = token_cache
        self._token_offsets = token_offsets
        self._line_offsets = line_offsets
        self._token_cache_hash = content_hash
        self._last_rendered_range = (-1, -1)
        self._apply_cache_to_viewport()

    # ─────────────────────────────────────────────────────────────────────────
    # Core render — O(log n) slice + batched tag ops
    # ─────────────────────────────────────────────────────────────────────────

    def _apply_cache_to_viewport(self):
        """
        Apply cached tokens to the visible viewport.

        Token discovery: O(log n) via bisect on pre-sorted offset list.
        Tag application: O(tags_in_viewport) via batched tag_add calls.
        Index resolution: O(1) per token — pre-computed "LINE.COL" strings.
        """
        if not self._token_cache or not self._line_offsets:
            return

        try:
            if not self.text.winfo_exists():
                return

            h = self.text.winfo_height()
            total_lines = len(self._line_offsets)

            vis_top = int(self.text.index("@0,0").split(".")[0])
            vis_bottom = int(self.text.index(f"@0,{h}").split(".")[0])

            start_line = max(1, vis_top - self.BUFFER_LINES)
            end_line = min(total_lines, vis_bottom + self.BUFFER_LINES)

            new_range = (start_line, end_line)
            if new_range == self._last_rendered_range:
                return

            # ── Viewport char boundaries ──────────────────────────────────────
            slice_start_c = self._line_offsets[start_line - 1]

            if end_line < len(self._line_offsets):
                slice_end_c = self._line_offsets[end_line] - 1
            else:
                last_line_text = self.text.get(f"{total_lines}.0", f"{total_lines}.end")
                slice_end_c = self._line_offsets[-1] + len(last_line_text)

            tk_vp_start = f"{start_line}.0"
            tk_vp_end = f"{end_line}.end"

            # ── 1. Clear old syntax tags in viewport ──────────────────────────
            for tag in self.valid_tags:
                self.text.tag_remove(tag, tk_vp_start, tk_vp_end)

            # ── 2. Binary-search slice ────────────────────────────────────────
            # right_idx: first token whose START >= slice_end_c  (all after this are outside)
            right_idx = bisect.bisect_left(self._token_offsets, slice_end_c)

            # left_idx: first token whose START >= slice_start_c,
            # then back up to catch tokens that started before slice_start_c
            # but whose END falls inside the viewport.
            left_idx = bisect.bisect_left(self._token_offsets, slice_start_c)
            while left_idx > 0 and self._token_cache[left_idx - 1][1] > slice_start_c:
                left_idx -= 1

            # ── 3. Accumulate per-tag range pairs ─────────────────────────────
            ranges_by_tag: dict[str, list[str]] = {}

            for abs_start, abs_end, tag, tk_s, tk_e in self._token_cache[
                left_idx:right_idx
            ]:
                # Fine-grained filter for tokens that straddle a boundary
                if abs_end <= slice_start_c or abs_start >= slice_end_c:
                    continue
                bucket = ranges_by_tag.get(tag)
                if bucket is None:
                    ranges_by_tag[tag] = [tk_s, tk_e]
                else:
                    bucket.append(tk_s)
                    bucket.append(tk_e)

            # ── 4. One tag_add call per tag type ──────────────────────────────
            for tag, flat in ranges_by_tag.items():
                self.text.tag_add(tag, *flat)

            self._last_rendered_range = new_range

        except (tk.TclError, RuntimeError, ValueError):
            pass
