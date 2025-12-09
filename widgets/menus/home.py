"""
The home menu application functionality layer
\nHandles home menu services, and calls second layer support if required
\nSecond Layer Support (SLS): handles syntax highlighting, and intellisense for Python
"""

import customtkinter as ctk
import textwrap


class AddMacrosTab(ctk.CTkToplevel):
    def __init__(
        self,
        main_window,
        master,
        text_editor,
        switcher,
        status_button=None,
        *args,
        **kwargs,
    ):
        # Correct usage of super()
        super().__init__(master, *args, **kwargs)

        self.master = master
        self.main_window = main_window
        self.text_editor = text_editor
        self.status_button = status_button
        self.switcher = switcher

        self.mode = self.master._get_appearance_mode()

        # Window setup
        self.transient(main_window.window)
        self.attributes("-topmost", True)
        self.title("Macros Configuration")
        self.resizable(False, False)
        self.geometry("650x400")
        self.withdraw()
        self._apply_appearance_mode(self.master._get_appearance_mode())

        # Left frame
        self.left_frame = ctk.CTkFrame(
            self, corner_radius=5, border_width=0, width=200, height=392
        )
        self.left_frame.place(x=4, y=4)
        self.left_frame.pack_propagate(False)

        # Buttons
        self.classBtnMacro = ctk.CTkButton(
            self.left_frame,
            corner_radius=2,
            border_width=0,
            width=190,
            height=30,
            text="Class Snippet",
            font=("Segoe UI", 12),
            command=self.addClassMacro,
        )
        self.classBtnMacro.pack(fill="both", anchor="w", padx=2, pady=(5, 5))

        self.mainBtnMacro = ctk.CTkButton(
            self.left_frame,
            corner_radius=2,
            border_width=0,
            width=190,
            height=30,
            text="Main Function",
            font=("Segoe UI", 12),
            command=self.addMainMacro,
        )
        self.mainBtnMacro.pack(fill="both", anchor="w", padx=2, pady=(0, 5))

        self.funcBtnMacro = ctk.CTkButton(
            self.left_frame,
            corner_radius=2,
            border_width=0,
            width=190,
            height=30,
            text="Function Snippet",
            font=("Segoe UI", 12),
            command=self.addFunctionMacro,
        )
        self.funcBtnMacro.pack(fill="both", anchor="w", padx=2, pady=(0, 5))

        self.tryExceptBtnMacro = ctk.CTkButton(
            self.left_frame,
            corner_radius=2,
            border_width=0,
            width=190,
            height=30,
            text="Try-Except Block",
            font=("Segoe UI", 12),
            command=self.addTryExceptMacro,
        )
        self.tryExceptBtnMacro.pack(fill="both", anchor="w", padx=2, pady=(0, 5))

        self.headerBtnMacro = ctk.CTkButton(
            self.left_frame,
            corner_radius=2,
            border_width=0,
            width=190,
            height=30,
            text="Header Comment",
            font=("Segoe UI", 12),
            command=self.addHeadMacro,
        )
        self.headerBtnMacro.pack(fill="both", anchor="w", padx=2, pady=(0, 5))

        self.tailBtnMacro = ctk.CTkButton(
            self.left_frame,
            corner_radius=2,
            border_width=0,
            width=190,
            height=30,
            text="Tail Comment",
            font=("Segoe UI", 12),
            command=self.addTailMacro,
        )
        self.tailBtnMacro.pack(fill="both", anchor="w", padx=2, pady=(0, 5))

        # Right Components
        self.title_label = ctk.CTkLabel(
            self,
            text="Add a Code Snippet",
            font=("Segoe UI", 20),
            text_color="#C4C4C4" if self.mode == "dark" else "#1E1E1E",
            corner_radius=0,
        )
        self.title_label.place(x=220, y=8)

        self.add_button = ctk.CTkButton(
            self.left_frame,
            text="Add Macro",
            font=("Segoe UI", 12),
            fg_color="#005393",
            hover_color="#003660",
            corner_radius=5,
            border_width=0,
            command=self.addMacroFn,
        )

        self.description_label = ctk.CTkLabel(
            self,
            text="",
            font=("Segoe UI", 12),
            text_color="#C4C4C4" if self.mode == "dark" else "#1E1E1E",
            corner_radius=0,
            anchor="w",
            justify="left",
        )

        self.image = ctk.CTkLabel(self, text="", corner_radius=0)
        self.image.place(x=220, y=40)

        self.textbox = ctk.CTkTextbox(
            self, width=410, height=200, font=("Consolas", 15)
        )
        self.textbox.configure(state=ctk.DISABLED)
        self.textbox.place(x=220, y=80)

        self.classCode = textwrap.dedent(
            """class Macro:
    def __init__(self, var1, var2, var3):
        self.var1 = var1
        self.var2 = var2
        self.var3 = var3

    def function(self):
        return
"""
        )
        self.mainCode = textwrap.dedent(
            """if __name__ == '__main__':
    run_program()
    return
"""
        )
        self.tryExceptCode = textwrap.dedent(
            """try:
    if var1:
        runCommand_1()
    else:
        runCommand_2()
except Exception as e:
    print("Error in the current line: {e}")
"""
        )
        self.functionCode = textwrap.dedent(
            """def function:
    return
"""
        )
        self.headCode = textwrap.dedent(
            """'''Author:
Date:
Description:'''
"""
        )
        self.tailCode = textwrap.dedent(
            """'''COPYRIGHT 20XX BY COMPANY NAME
ALL RIGHTS RESERVED'''
"""
        )

        self.textbox.tag_config("keyword1", foreground="#81dfff")  # Variables
        self.textbox.tag_config("class", foreground="#42B78C")  # Class
        self.textbox.tag_config("method", foreground="#fff767")  # Methods/Functions
        self.textbox.tag_config("keyword2", foreground="#5587CA")  # Other Keywords
        self.textbox.tag_config("comments", foreground="#C09761")  # Comments

    # Function to tag all occurrences of a word
    def tag_word(self, word, tag_name):
        start = "1.0"
        while True:
            pos = self.textbox.search(word, start, stopindex="end")
            if not pos:
                break
            end = f"{pos}+{len(word)}c"
            self.textbox.tag_add(tag_name, pos, end)
            start = end

    def addClassMacro(self):
        self.title_label.configure(text="Class Snippet")
        self.description_label.configure(
            text="Description:\nAdds a class snippet with a default name to the current cursor location"
        )
        self.description_label.place(x=220, y=350)
        self.add_button.pack(fill="x", side="bottom", pady=8, padx=8)
        self.textbox.configure(state=ctk.NORMAL)
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", self.classCode)

        self.tag_word("class", "keyword2")
        self.tag_word("Macro", "class")
        self.tag_word("def", "keyword2")
        self.tag_word("__init__", "method")
        self.tag_word("function", "method")
        self.tag_word("return", "keyword2")
        self.tag_word("var1", "keyword1")
        self.tag_word("var2", "keyword1")
        self.tag_word("var3", "keyword1")
        self.tag_word("self", "keyword2")

        self.textbox.configure(state=ctk.DISABLED)

    def addFunctionMacro(self):
        self.title_label.configure(text="Function Snippet")
        self.description_label.configure(
            text="Description:\nAdds a function snippet with a default name to the current cursor location"
        )
        self.description_label.place(x=220, y=350)
        self.add_button.pack(fill="x", side="bottom", pady=8, padx=8)
        self.textbox.configure(state=ctk.NORMAL)
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", self.functionCode)

        self.tag_word("def", "keyword2")
        self.tag_word("function", "method")
        self.tag_word("return", "keyword2")

        self.textbox.configure(state=ctk.DISABLED)

    def addMainMacro(self):
        self.title_label.configure(text="Main Function Snippet")
        self.description_label.configure(
            text="Description:\nAdds, at the current loaction of the cursor, the main function snippet\nactivation function (main)"
        )
        self.description_label.place(x=220, y=350)
        self.add_button.pack(fill="x", side="bottom", pady=8, padx=8)
        self.textbox.configure(state=ctk.NORMAL)
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", self.mainCode)

        self.tag_word("if", "method")
        self.tag_word("__name__", "keyword2")
        self.tag_word("__main__", "keyword2")
        self.tag_word("run_program", "method")
        self.tag_word("return", "method")

        self.textbox.configure(state=ctk.DISABLED)

    def addTryExceptMacro(self):
        self.title_label.configure(text="Try-Except Snippet")
        self.description_label.configure(
            text="Description:\nAdds, at the current loaction of the cursor, a try-except logical block"
        )
        self.description_label.place(x=220, y=350)
        self.add_button.pack(fill="x", side="bottom", pady=8, padx=8)
        self.textbox.configure(state=ctk.NORMAL)
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", self.tryExceptCode)

        self.tag_word("try", "keyword2")
        self.tag_word("if", "keyword2")
        self.tag_word("else", "keyword2")
        self.tag_word("except", "keyword2")
        self.tag_word("Exception", "keyword2")
        self.tag_word("var1", "keyword1")
        self.tag_word("e", "keyword1")
        self.tag_word("runCommand_1", "method")
        self.tag_word("runCommand_2", "method")
        self.tag_word("print", "method")

        self.textbox.configure(state=ctk.DISABLED)

    def addHeadMacro(self):
        self.title_label.configure(text="Header Comment")
        self.description_label.configure(text="Description:\nAdds a header comment")
        self.description_label.place(x=220, y=350)
        self.add_button.pack(fill="x", side="bottom", pady=8, padx=8)
        self.textbox.configure(state=ctk.NORMAL)
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", self.headCode)

        self.tag_word(f"{self.headCode}", "comments")
        self.textbox.configure(state=ctk.DISABLED)

    def addTailMacro(self):
        self.title_label.configure(text="Tail Comment")
        self.description_label.configure(text="Description:\nAdds a tail comment")
        self.description_label.place(x=220, y=350)
        self.add_button.pack(fill="x", side="bottom", pady=8, padx=8)
        self.textbox.configure(state=ctk.NORMAL)
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", self.tailCode)

        self.tag_word(f"{self.tailCode}", "comments")
        self.textbox.configure(state=ctk.DISABLED)

    def removePlaceholderText(self):
        self.switcher._hide_placeholder()

    def addMacroFn(self):
        self.removePlaceholderText()
        snippet = self.textbox.get("1.0", "end-1c")
        self.text_editor.insert("insert", "\n" + snippet)

    def run(self):
        self.deiconify()
        self.lift()
        if self.status_button:
            self.status_button.configure(text="Waiting to choose a macro")


def codeSnippetOpen(app):
    pass


def refreshFiles(app):
    pass


def saveAllFiles(app):
    pass


# ======================================


def cutFiles(textbox):
    pass


def copyFiles(textbox):
    pass


def pasteFiles(textbox):
    pass


def undoChange(textbox):
    pass


def redoChange(textbox):
    pass


def deleteCode(textbox):
    pass


# ======================================


class ConfigureSyntax(ctk.CTkToplevel):
    def __init__(
        self, main_window, master, text_editor, status_button=None, *args, **kwargs
    ):
        # Correct usage of super()
        super().__init__(master, *args, **kwargs)

        self.master = master
        self.main_window = main_window
        self.text_editor = text_editor
        self.status_button = status_button
        self.mode = self.master._get_appearance_mode()

        # Window setup
        self.transient(main_window.window)
        self.attributes("-topmost", True)
        self.title("Syntax Configuration")
        self.resizable(False, False)
        self.geometry("650x400")
        self.withdraw()
        self._apply_appearance_mode(self.master._get_appearance_mode())

        # Left frame
        self.left_frame = ctk.CTkFrame(
            self, corner_radius=5, border_width=0, width=200, height=392
        )
        self.left_frame.place(x=4, y=4)
        self.left_frame.pack_propagate(False)

        # Buttons
        self.lightThemeBtn = ctk.CTkButton(
            self.left_frame,
            corner_radius=2,
            border_width=0,
            width=190,
            height=30,
            text="Normal Light",
            font=("Segoe UI", 12),
        )
        self.lightThemeBtn.pack(fill="both", anchor="w", padx=2, pady=(5, 5))

        self.darkThemeBtn = ctk.CTkButton(
            self.left_frame,
            corner_radius=2,
            border_width=0,
            width=190,
            height=30,
            text="Normal Dark",
            font=("Segoe UI", 12),
        )
        self.darkThemeBtn.pack(fill="both", anchor="w", padx=2, pady=(0, 5))

        self.darkPlusThemeBtn = ctk.CTkButton(
            self.left_frame,
            corner_radius=2,
            border_width=0,
            width=190,
            height=30,
            text="Dark Plus",
            font=("Segoe UI", 12),
        )
        self.darkPlusThemeBtn.pack(fill="both", anchor="w", padx=2, pady=(0, 5))

        self.atomicThemeBtn = ctk.CTkButton(
            self.left_frame,
            corner_radius=2,
            border_width=0,
            width=190,
            height=30,
            text="Atomic",
            font=("Segoe UI", 12),
        )
        self.atomicThemeBtn.pack(fill="both", anchor="w", padx=2, pady=(0, 5))

        self.solorizedThemeLightBtn = ctk.CTkButton(
            self.left_frame,
            corner_radius=2,
            border_width=0,
            width=190,
            height=30,
            text="Solorized Light",
            font=("Segoe UI", 12),
        )
        self.solorizedThemeLightBtn.pack(fill="both", anchor="w", padx=2, pady=(0, 5))

        self.monokaiThemeBtn = ctk.CTkButton(
            self.left_frame,
            corner_radius=2,
            border_width=0,
            width=190,
            height=30,
            text="Monokai",
            font=("Segoe UI", 12),
        )
        self.monokaiThemeBtn.pack(fill="both", anchor="w", padx=2, pady=(0, 5))

        self.oceanicThemeBtn = ctk.CTkButton(
            self.left_frame,
            corner_radius=2,
            border_width=0,
            width=190,
            height=30,
            text="Oceanic",
            font=("Segoe UI", 12),
        )
        self.oceanicThemeBtn.pack(fill="both", anchor="w", padx=2, pady=(0, 5))

        self.nightOwlThemeBtn = ctk.CTkButton(
            self.left_frame,
            corner_radius=2,
            border_width=0,
            width=190,
            height=30,
            text="Night Owl",
            font=("Segoe UI", 12),
        )
        self.nightOwlThemeBtn.pack(fill="both", anchor="w", padx=2, pady=(0, 5))

        self.gruvboxThemeBtn = ctk.CTkButton(
            self.left_frame,
            corner_radius=2,
            border_width=0,
            width=190,
            height=30,
            text="Gruvbox",
            font=("Segoe UI", 12),
        )
        self.gruvboxThemeBtn.pack(fill="both", anchor="w", padx=2, pady=(0, 5))

        # Right Components
        self.title_label = ctk.CTkLabel(
            self,
            text="Configure Theme",
            font=("Segoe UI", 20),
            text_color="#C4C4C4" if self.mode == "dark" else "#1E1E1E",
            corner_radius=0,
        )
        self.title_label.place(x=220, y=8)

        self.add_button = ctk.CTkButton(
            self.left_frame,
            text="Change Theme",
            font=("Segoe UI", 12),
            fg_color="#005393",
            hover_color="#003660",
            corner_radius=5,
            border_width=0,
        )

        self.description_label = ctk.CTkLabel(
            self,
            text="",
            font=("Segoe UI", 12),
            text_color="#C4C4C4" if self.mode == "dark" else "#1E1E1E",
            corner_radius=0,
            anchor="w",
            justify="left",
        )

        self.image = ctk.CTkLabel(self, text="", corner_radius=0)
        self.image.place(x=220, y=40)

        self.textbox = ctk.CTkTextbox(
            self, width=410, height=260, font=("Consolas", 15)
        )
        self.textbox.configure(state=ctk.DISABLED)
        self.textbox.place(x=220, y=50)

    def changeFontTheme():
        pass

    def run(self):
        self.deiconify()
        self.lift()
        if self.status_button:
            self.status_button.configure(text="Waiting to choose a macro")
