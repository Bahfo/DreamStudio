import os
import tkinter as tk
import threading
from pygments import lex
from pygments.lexers import get_lexer_by_name, get_lexer_for_filename

class Highlighter:
    def __init__(self, master, language="", *args, **kwargs):
        self.text = master
        self.base = master.base
        self.language = language
        self.debounce_id = None
        self.last_visible_range = (None, None)

        # 1. Lexer setup
        try:
            if language:
                self.lexer = get_lexer_by_name(language)
            else:
                self.lexer = get_lexer_for_filename(
                    os.path.basename(master.path),
                    inencoding=master.encoding,
                    encoding=master.encoding,
                )
        except Exception:
            self.lexer = None
            return

        # 2. Register the colors (The missing piece!)
        self.setup_highlight_tags()

        # 3. Proxy the yview to handle scrolling dynamically
        self.original_yview = master.yview
        master.yview = self.proxy_yview

    def setup_highlight_tags(self):
        """Maps Pygments tokens to Tkinter tag colors from your settings."""
        for token_path, color in self.base.settings.syntax.items():
            # Standardize tag names to "Token.Name" format
            tag_name = f"Token.{token_path}"
            self.text.tag_configure(tag_name, foreground=color)

    def proxy_yview(self, *args):
        """Intercepts scroll commands and triggers a highlight update."""
        result = self.original_yview(*args)
        self.highlight()
        return result

    def highlight(self, event=None):
        """Instant local update + debounced background full-screen update."""
        # Fast update for the current line to keep typing responsive
        self._highlight_current_line()

        # Debounce the heavy lifting (50ms is usually the sweet spot)
        if self.debounce_id:
            self.text.after_cancel(self.debounce_id)
        self.debounce_id = self.text.after(50, self.perform_full_update)

    def _highlight_current_line(self):
        """Synchronous highlight of the active line."""
        cursor_pos = self.text.index(tk.INSERT)
        start = f"{cursor_pos} linestart"
        end = f"{cursor_pos} lineend"
        self._apply_lexing_to_range(start, end)

    def perform_full_update(self):
        """Visible area check and threading trigger."""
        start = self.text.index("@0,0 linestart")
        end = self.text.index(f"@0,{self.text.winfo_height()} lineend")
        
        if (start, end) == self.last_visible_range:
            return
        
        self.last_visible_range = (start, end)
        threading.Thread(target=self._async_lex, args=(start, end), daemon=True).start()

    def _async_lex(self, start, end):
        """Heavy background processing."""
        try:
            content = self.text.get(start, end)
            tokens = list(lex(content, self.lexer))
            # Send back to main thread for UI update
            self.text.after(0, lambda: self._apply_token_list(tokens, start, end))
        except Exception as e:
            print(f"Highlighting error: {e}")

    def _apply_token_list(self, tokens, start, end):
        """Bulk update of tags in the visible range."""
        # Clear old tags in this range
        for token_path in self.base.settings.syntax.keys():
            self.text.tag_remove(f"Token.{token_path}", start, end)

        self.text.mark_set("range_ptr", start)
        for token, value in tokens:
            # Pygments returns token objects; we need the string representation
            tag_name = str(token)
            end_ptr = self.text.index(f"range_ptr + {len(value)}c")
            
            # Apply tag if it exists in our theme
            self.text.tag_add(tag_name, "range_ptr", end_ptr)
            self.text.mark_set("range_ptr", end_ptr)

    def _apply_lexing_to_range(self, start, end):
        """Small-scale synchronous lexing for the current line."""
        content = self.text.get(start, end)
        for token_path in self.base.settings.syntax.keys():
            self.text.tag_remove(f"Token.{token_path}", start, end)
            
        self.text.mark_set("line_ptr", start)
        for token, value in lex(content, self.lexer):
            tag_name = str(token)
            end_ptr = self.text.index(f"line_ptr + {len(value)}c")
            self.text.tag_add(tag_name, "line_ptr", end_ptr)
            self.text.mark_set("line_ptr", end_ptr)