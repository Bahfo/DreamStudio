import customtkinter as ctk
import re

class KeywordSearch(ctk.CTkToplevel):
    def __init__(self, main_app, text_frame, status_button=None):
        super().__init__(main_app.window)
        self.main_app = main_app
        self.text_frame = text_frame
        self.status_button = status_button
        self.matches = []
        self.current_match_index = 0

        if self.status_button:
            self.status_button.configure(text="search menu opened")

        self.title("Find and Search")
        self.geometry("350x150")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.withdraw()
        self.transient(main_app.window)

        label = ctk.CTkLabel(
            self, text="Enter Keyword/Sentence/etc", font=("Arial", 12)
        )
        label.pack(pady=(20, 5))

        self.file_naming_box = ctk.CTkEntry(self, width=250)
        self.file_naming_box.place(x=350 / 2, y=150 / 2, anchor="center")

        confirm_button = ctk.CTkButton(
            self, text="Search", width=100, corner_radius=6, command=self.searching
        )
        confirm_button.place(x=100 / 2, y=100)
        confirm_button.focus_set()
        self.bind("<Return>", lambda e: confirm_button.invoke())

        self.next_search_btn = ctk.CTkButton(
            self,
            text="\u2b9f",
            width=40,
            corner_radius=6,
            state=ctk.DISABLED,
            command=self.next_search_match,
        )
        self.next_search_btn.place(x=260, y=100)

        self.previous_search_btn = ctk.CTkButton(
            self,
            text="\u2b9d",
            width=40,
            corner_radius=6,
            state=ctk.DISABLED,
            command=self.previous_search_match,
        )
        self.previous_search_btn.place(x=210, y=100)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def show(self):
        self.deiconify()
        self.lift()

    def searching(self):
        text_to_search = self.file_naming_box.get()
        full_text = self.text_frame.get("1.0", "end-1c")

        self.main_app.text_editor.tag_remove("highlight", "1.0", "end-1c")
        self.matches = list(re.finditer(re.escape(text_to_search), full_text))
        if self.matches:
            self.current_match_index = 0
            first_match = self.matches[self.current_match_index]
            start_index = f"1.0+{first_match.start()}c"
            self.main_app.text_editor.mark_set("insert", start_index)
            self.main_app.text_editor.see(start_index)
            for match in self.matches:
                start = f"1.0+{match.start()}c"
                end = f"1.0+{match.end()}c"
                self.main_app.text_editor.tag_add("highlight", start, end)
            self.main_app.text_editor.tag_config(
                "highlight", background="#633B24", foreground="#FFFFFF"
            )
            if self.status_button:
                self.status_button.configure(text="Search found successfully!")
            self.next_search_btn.configure(state=ctk.NORMAL)
            self.previous_search_btn.configure(state=ctk.NORMAL)
        else:
            if self.status_button:
                self.status_button.configure(text="No matches found!")

    def next_search_match(self):
        if not self.matches:
            return
        self.current_match_index = (self.current_match_index + 1) % len(self.matches)
        index = f"1.0+{self.matches[self.current_match_index].start()}c"
        self.main_app.text_editor.mark_set("insert", index)
        self.main_app.text_editor.see(index)

    def previous_search_match(self):
        if not self.matches:
            return
        self.current_match_index = (self.current_match_index - 1) % len(self.matches)
        index = f"1.0+{self.matches[self.current_match_index].start()}c"
        self.main_app.text_editor.mark_set("insert", index)
        self.main_app.text_editor.see(index)

    def on_close(self):
        self.main_app.text_editor.tag_remove("highlight", "1.0", "end-1c")
        self.destroy()