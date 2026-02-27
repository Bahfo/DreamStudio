import os
import tkinter as tk
import threading
from pygments import lex
from pygments.lexers import get_lexer_by_name, get_lexer_for_filename
from pygments.lexers.special import TextLexer

class Highlighter:
    def __init__(self, master, language="", *args, **kwargs):
        self.text = master
        self.base = master.base
        self.language = language
        self.debounce_id = None
        self.last_content_hash = None
        self.last_visible_range = (None, None)
        
        try:
            if language:
                self.lexer = get_lexer_by_name(language)
            else:
                self.lexer = get_lexer_for_filename(
                    os.path.basename(master.path),
                    encoding=master.encoding,
                )
        except Exception:
            self.lexer = TextLexer()

        self.valid_tags = set()
        self.setup_highlight_tags()

        self.original_yview = master.yview
        master.yview = self.proxy_yview
        self.text.bind("<KeyRelease>", self.highlight)
        self.text.bind("<<Paste>>", self.highlight)

    def setup_highlight_tags(self):
        for token_path, color in self.base.settings.syntax.items():
            tag_name = f"Token.{token_path}"
            self.text.tag_configure(tag_name, foreground=color)
            self.valid_tags.add(tag_name)

    def proxy_yview(self, *args):
        result = self.original_yview(*args)
        self.highlight()
        return result

    def highlight(self, event=None):
        if self.debounce_id:
            self.text.after_cancel(self.debounce_id)
        self.debounce_id = self.text.after(20, self.perform_full_update)

    def _get_char_offset(self, content_lines, line_num):
        """Calculates character offset from a list of lines efficiently."""
        # line_num is 1-based from Tkinter
        if line_num <= 1: return 0
        # Sum length of all lines before the target line + newlines
        return sum(len(line) + 1 for line in content_lines[:line_num - 1])

    def perform_full_update(self):
        try:
            # 1. Get view boundaries
            v_start = self.text.index("@0,0 linestart")
            v_end = self.text.index(f"@0,{self.text.winfo_height()} lineend")
            
            # 2. Extract line numbers safely
            # We use 'end-1c' because Tkinter always adds a hidden newline at the very end
            total_lines = int(self.text.index("end-1c").split('.')[0])
            
            start_line = max(1, int(v_start.split('.')[0]) - 5)
            end_line = min(total_lines, int(v_end.split('.')[0]) + 5)
            
            # 3. Robust index format: "line.0" to "line.end"
            tk_start = f"{start_line}.0"
            tk_end = f"{end_line}.end" 

            content = self.text.get("1.0", "end-1c")
        except (tk.TclError, ValueError, AttributeError):
            # If the widget is being destroyed or isn't ready, just exit
            return

        content_lines = content.split('\n')
        
        # Calculate offsets in pure Python (much faster than calling the widget)
        view_start_off = self._get_char_offset(content_lines, start_line)
        view_end_off = self._get_char_offset(content_lines, end_line + 1)

        # 4. Debounce check
        content_hash = hash(content)
        if content_hash == self.last_content_hash and (v_start, v_end) == self.last_visible_range:
            return
        
        self.last_content_hash = content_hash
        self.last_visible_range = (v_start, v_end)

        threading.Thread(
            target=self._async_lex, 
            args=(content, view_start_off, view_end_off, tk_start, tk_end), 
            daemon=True
        ).start()

    def _apply_visible_tokens(self, tokens, tk_start, tk_end):
        """Batch updates the UI. Uses character offsets for stability."""
        try:
            # Check if widget still exists
            if not self.text.winfo_exists():
                return

            # Safety check: Ensure our end index hasn't moved past the current end
            # (e.g., if the user deleted a huge chunk of text while the thread ran)
            actual_end = self.text.index("end-1c")
            if self.text.compare(tk_end, ">", actual_end):
                tk_end = actual_end

            # 1. Clear tags in the visible block only
            for tag in self.valid_tags:
                self.text.tag_remove(tag, tk_start, tk_end)

            # 2. Add tags using character offsets relative to 1.0
            # This is the most stable way to handle indices during rapid edits
            for tag_name, start_off, t_len in tokens:
                s_idx = f"1.0 + {start_off}c"
                e_idx = f"1.0 + {start_off + t_len}c"
                self.text.tag_add(tag_name, s_idx, e_idx)
                
        except (tk.TclError, RuntimeError):
            # Catching TclErrors from rapid deletions or window closure
            pass

    def _async_lex(self, content, start_off, end_off, tk_start, tk_end):
        try:
            tokens = list(lex(content, self.lexer))
            visible_tokens = []
            current_off = 0
            
            for token, value in tokens:
                t_len = len(value)
                t_end = current_off + t_len
                
                # Filter tokens to only include those in the visible buffer
                if t_end > start_off and current_off < end_off:
                    tag_name = str(token)
                    if tag_name in self.valid_tags:
                        visible_tokens.append((tag_name, current_off, t_len))
                
                current_off = t_end
                if current_off > end_off: break
            
            # Update UI on main thread
            self.text.after(0, lambda: self._apply_visible_tokens(visible_tokens, tk_start, tk_end))
        except Exception as e:
            print(f"Highlight error: {e}")
