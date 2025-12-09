import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinter.simpledialog import askstring
import os
import subprocess
import threading
import queue
from pathlib import Path
from pygments import lex
from pygments.lexers import get_lexer_by_name


class VSCodeIDE:
    def __init__(self, root):
        self.root = root
        self.root.title("PyCode IDE")
        self.root.geometry("1200x800")

        # Theme and style
        self.style = ttk.Style()
        self.dark_mode = False
        self.apply_theme()

        # Data structures
        self.open_files = {}  # {tab_id: {"path": path, "content": content}}
        self.current_folder = None
        self.auto_save = False

        # Queue for thread-safe terminal output
        self.output_queue = queue.Queue()

        # Menu bar
        self.create_menu()

        # Main layout: PanedWindow for resizable panes
        self.main_pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True)

        # Left pane: File explorer
        self.left_frame = ttk.Frame(self.main_pane)
        self.main_pane.add(self.left_frame, minsize=200)
        self.create_file_explorer()

        # Right pane: Editor and terminal
        self.right_pane = tk.PanedWindow(self.main_pane, orient=tk.VERTICAL)
        self.main_pane.add(self.right_pane, minsize=600)

        # Editor (tabbed)
        self.editor_frame = ttk.Frame(self.right_pane)
        self.right_pane.add(self.editor_frame, minsize=400)
        self.create_editor()

        # Terminal
        self.terminal_frame = ttk.Frame(self.right_pane)
        self.right_pane.add(self.terminal_frame, minsize=150)
        self.create_terminal()

        # Status bar
        self.status_bar = ttk.Label(self.root, text="Ready", anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Bind shortcuts
        self.bind_shortcuts()

        # Start checking the output queue
        self.check_output_queue()

    def apply_theme(self):
        if self.dark_mode:
            self.style.theme_use("clam")
            self.root.configure(bg="#2d2d2d")
            self.style.configure("TFrame", background="#2d2d2d")
            self.style.configure("TLabel", background="#2d2d2d", foreground="white")
            self.style.configure(
                "Treeview",
                background="#3c3c3c",
                foreground="white",
                fieldbackground="#3c3c3c",
            )
            self.style.configure("TNotebook", background="#2d2d2d")
            self.style.configure(
                "TNotebook.Tab", background="#3c3c3c", foreground="white"
            )
        else:
            self.style.theme_use("default")
            self.root.configure(bg="white")

    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(
            label="New File", command=self.new_file, accelerator="Ctrl+N"
        )
        file_menu.add_command(
            label="Open File", command=self.open_file, accelerator="Ctrl+O"
        )
        file_menu.add_command(label="Open Folder", command=self.open_folder)
        file_menu.add_command(
            label="Save", command=self.save_file, accelerator="Ctrl+S"
        )
        file_menu.add_command(
            label="Save As", command=self.save_as_file, accelerator="Ctrl+Shift+S"
        )
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", command=self.undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Redo", command=self.redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(
            label="Find", command=self.find_text, accelerator="Ctrl+F"
        )
        edit_menu.add_command(
            label="Replace", command=self.replace_text, accelerator="Ctrl+H"
        )

        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Toggle Dark Mode", command=self.toggle_theme)
        view_menu.add_command(label="Toggle Auto-Save", command=self.toggle_auto_save)

        # Run menu
        run_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Run", menu=run_menu)
        run_menu.add_command(
            label="Run in Terminal", command=self.run_in_terminal, accelerator="F5"
        )

    def create_file_explorer(self):
        ttk.Label(self.left_frame, text="Explorer").pack(anchor=tk.W)
        self.tree = ttk.Treeview(self.left_frame)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.heading("#0", text="Files")
        self.tree.bind("<Double-1>", self.open_file_from_tree)

    def create_editor(self):
        self.notebook = ttk.Notebook(self.editor_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

    def create_terminal(self):
        ttk.Label(self.terminal_frame, text="Terminal").pack(anchor=tk.W)
        self.terminal = scrolledtext.ScrolledText(
            self.terminal_frame, height=10, wrap=tk.WORD
        )
        self.terminal.pack(fill=tk.BOTH, expand=True)
        self.terminal.insert(tk.END, "> ")
        self.terminal.bind("<Return>", self.run_command)

    def bind_shortcuts(self):
        self.root.bind("<Control-n>", lambda e: self.new_file())
        self.root.bind("<Control-o>", lambda e: self.open_file())
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-Shift-S>", lambda e: self.save_as_file())
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())
        self.root.bind("<Control-f>", lambda e: self.find_text())
        self.root.bind("<Control-h>", lambda e: self.replace_text())
        self.root.bind("<F5>", lambda e: self.run_in_terminal())

    def new_file(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Untitled")
        text_area = scrolledtext.ScrolledText(tab, wrap=tk.WORD, undo=True)
        text_area.pack(fill=tk.BOTH, expand=True)
        text_area.bind("<KeyRelease>", self.on_text_change)
        tab_id = self.notebook.tabs()[-1]
        self.open_files[tab_id] = {"path": None, "content": "", "text_area": text_area}

    def open_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.load_file(file_path)

    def open_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.current_folder = Path(folder_path)
            self.populate_tree()

    def populate_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.insert_tree("", self.current_folder)

    def insert_tree(self, parent, path):
        for item in path.iterdir():
            iid = self.tree.insert(parent, "end", text=item.name, open=False)
            if item.is_dir():
                self.tree.insert(iid, "end")  # Placeholder

    def open_file_from_tree(self, event):
        selected = self.tree.selection()
        if selected:
            item_text = self.tree.item(selected, "text")
            full_path = self.current_folder / item_text
            if full_path.is_file():
                self.load_file(str(full_path))

    def load_file(self, file_path):
        with open(file_path, "r") as f:
            content = f.read()
        self.new_file()
        tab_id = self.notebook.tabs()[-1]
        self.open_files[tab_id]["path"] = file_path
        self.open_files[tab_id]["content"] = content
        self.open_files[tab_id]["text_area"].insert(tk.END, content)
        self.notebook.tab(tab_id, text=Path(file_path).name)
        self.apply_syntax_highlighting(tab_id)

    def save_file(self):
        tab_id = self.notebook.select()
        if tab_id in self.open_files:
            path = self.open_files[tab_id]["path"]
            if path:
                content = self.open_files[tab_id]["text_area"].get(1.0, tk.END).strip()
                with open(path, "w") as f:
                    f.write(content)
                self.open_files[tab_id]["content"] = content
                self.status_bar.config(text=f"Saved: {path}")
            else:
                self.save_as_file()

    def save_as_file(self):
        tab_id = self.notebook.select()
        if tab_id in self.open_files:
            file_path = filedialog.asksaveasfilename(defaultextension=".txt")
            if file_path:
                self.open_files[tab_id]["path"] = file_path
                self.save_file()
                self.notebook.tab(tab_id, text=Path(file_path).name)

    def undo(self):
        tab_id = self.notebook.select()
        if tab_id in self.open_files:
            self.open_files[tab_id]["text_area"].edit_undo()

    def redo(self):
        tab_id = self.notebook.select()
        if tab_id in self.open_files:
            self.open_files[tab_id]["text_area"].edit_redo()

    def find_text(self):
        tab_id = self.notebook.select()
        if tab_id in self.open_files:
            find_str = askstring("Find", "Enter text to find:")
            if find_str:
                text_area = self.open_files[tab_id]["text_area"]
                start = text_area.search(find_str, 1.0, tk.END)
                if start:
                    text_area.tag_add(tk.SEL, start, f"{start}+{len(find_str)}c")
                    text_area.mark_set(tk.INSERT, start)
                    text_area.see(start)

    def replace_text(self):
        tab_id = self.notebook.select()
        if tab_id in self.open_files:
            find_str = askstring("Replace", "Find:")
            replace_str = askstring("Replace", "Replace with:")
            if find_str and replace_str:
                text_area = self.open_files[tab_id]["text_area"]
                content = text_area.get(1.0, tk.END)
                new_content = content.replace(find_str, replace_str)
                text_area.delete(1.0, tk.END)
                text_area.insert(tk.END, new_content)

    def run_in_terminal(self):
        tab_id = self.notebook.select()
        if tab_id in self.open_files and self.open_files[tab_id]["path"]:
            path = self.open_files[tab_id]["path"]
            if path.endswith(".py"):
                quoted_path = f'"{path}"'  # Quote to handle spaces
                cmd = f"python {quoted_path}"
                self.run_command_in_terminal(cmd)

    def run_command_in_terminal(self, cmd):
        print(f"Running command: {cmd}")  # Debug print
        self.terminal.insert(tk.END, f"\n> {cmd}\n")
        threading.Thread(target=self.execute_command, args=(cmd,)).start()

    def execute_command(self, cmd):
        try:
            # Use Popen for better control over output
            cwd = str(self.current_folder) if self.current_folder else os.getcwd()
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd,
            )
            print(f"Process started with PID: {process.pid}")  # Debug print

            # Read output line by line
            for line in iter(process.stdout.readline, ""):
                if line:
                    self.output_queue.put(line)
            for line in iter(process.stderr.readline, ""):
                if line:
                    self.output_queue.put(line)

            process.stdout.close()
            process.stderr.close()
            process.wait()
            print(
                f"Process finished with return code: {process.returncode}"
            )  # Debug print
            self.output_queue.put("\n> ")  # Prompt for next command
        except Exception as e:
            print(f"Error in execute_command: {e}")  # Debug print
            self.output_queue.put(f"Error: {e}\n> ")

    def run_command(self, event):
        # Get the command from the current line (after "> ")
        lines = self.terminal.get(1.0, tk.END).split("\n")
        if lines and lines[-2].startswith("> "):  # Last meaningful line
            cmd = lines[-2][2:].strip()
            if cmd:
                self.run_command_in_terminal(cmd)

    def check_output_queue(self):
        # Check queue for output and update terminal (called from main thread)
        try:
            while True:
                output = self.output_queue.get_nowait()
                self.terminal.insert(tk.END, output)
                self.terminal.see(tk.END)
        except queue.Empty:
            pass
        self.root.after(
            50, self.check_output_queue
        )  # Check every 50ms for faster updates

    def on_text_change(self, event):
        tab_id = self.notebook.select()
        if tab_id in self.open_files and self.auto_save:
            self.save_file()
        self.apply_syntax_highlighting(tab_id)
        self.update_status()

    def apply_syntax_highlighting(self, tab_id):
        if tab_id in self.open_files:
            path = self.open_files[tab_id]["path"]
            if path:
                ext = Path(path).suffix
                lexer = get_lexer_by_name("python" if ext == ".py" else "text")
                text_area = self.open_files[tab_id]["text_area"]
                content = text_area.get(1.0, tk.END)
                # Basic highlighting (simplified; full implementation would require custom Text widget)
                # For now, just color keywords
                text_area.tag_configure("keyword", foreground="blue")
                for token, value in lex(content, lexer):
                    if token.name == "Keyword":
                        start = content.find(value)
                        end = start + len(value)
                        text_area.tag_add("keyword", f"1.0+{start}c", f"1.0+{end}c")

    def on_tab_change(self, event):
        self.update_status()

    def update_status(self):
        tab_id = self.notebook.select()
        if tab_id in self.open_files:
            path = self.open_files[tab_id]["path"] or "Untitled"
            text_area = self.open_files[tab_id]["text_area"]
            line, col = text_area.index(tk.INSERT).split(".")
            self.status_bar.config(text=f"{path} | Line {line}, Col {col}")

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()

    def toggle_auto_save(self):
        self.auto_save = not self.auto_save
        messagebox.showinfo(
            "Auto-Save", f"Auto-save {'enabled' if self.auto_save else 'disabled'}"
        )


if __name__ == "__main__":
    root = tk.Tk()
    app = VSCodeIDE(root)
    root.mainloop()
