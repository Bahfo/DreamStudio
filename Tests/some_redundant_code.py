#################################################################################################
# SYNTAX HIGHLIGHTER AND INTELLISENSE
#################################################################################################

intellisense = PythonIntellisense(window, text_editor)
text_editor.bind("<KeyRelease>", intellisense.on_key_release)

for syntax_tag_name, syntax_color in highlighter_ref[0].colors.items():
    text_editor.tag_config(syntax_tag_name, foreground=syntax_color)

def highlight_line(line_number):
    current_highlighter = highlighter_ref[0]
    line_text = text_editor.get(f"{line_number}.0", f"{line_number}.end")

    for tag in current_highlighter.colors.keys():
        text_editor.tag_remove(tag, f"{line_number}.0", f"{line_number}.end")

    if hasattr(current_highlighter, "special_logic_pattern"):
        for match in current_highlighter.special_logic_pattern.finditer(line_text):
            start = f"{line_number}.{match.start()}"
            end = f"{line_number}.{match.end()}"
            text_editor.tag_add("special_statements", start, end)

    for match in re.finditer(current_highlighter.token_pattern, line_text):
        token = match.group()
        start = f"{line_number}.{match.start()}"
        end   = f"{line_number}.{match.end()}"

        tag = None

        if "comments" in current_highlighter.dictionary and re.fullmatch(current_highlighter.dictionary["comments"], token):
            tag = "comments"
        elif "strings" in current_highlighter.dictionary and re.fullmatch(current_highlighter.dictionary["strings"], token):
            tag = "strings"
        elif "numbers" in current_highlighter.dictionary and re.fullmatch(current_highlighter.dictionary["numbers"], token):
            tag = "numbers"
        else:
            tag = current_highlighter.highlight_token(token)

        if not tag and hasattr(current_highlighter, "variables") and re.fullmatch(current_highlighter.variables, token):
            tag = "variables"

        if tag:
            text_editor.tag_add(tag, start, end)


def highlight_all():
    total_lines = int(text_editor.index('end-1c').split('.')[0])
    for line_number in range(1, total_lines + 1):
        highlight_line(line_number)


def on_return(event):
    text_editor.after(1, highlight_all)


def on_key_release(event):
    current_line = text_editor.index("insert").split(".")[0]
    highlight_line(current_line)


text_editor.bind("<KeyRelease>", on_key_release)
text_editor.bind("<Return>", on_return)



def choose_current_syntax(language):
    if language == 'Python':
        highlighter_ref[0] = PythonHighlighter()
    elif language == 'C':
        highlighter_ref[0] = CHighlighter()
    elif language == 'C++':
        highlighter_ref[0] = CPPHighlighter()
    elif language == 'Java':
        highlighter_ref[0] = JavaHighlighter()
    elif language == 'JavaScript':
        highlighter_ref[0] = JavascriptHighlighter()
    elif language == 'Rust':
        highlighter_ref[0] = RustHighlighter()
    elif language == 'HTML':
        highlighter_ref[0] = HTMLHighlighter()
    elif language == 'C Sharp':
        highlighter_ref[0] = CSharpHighlighter()
    elif language == 'PHP':
        highlighter_ref[0] = PHPHighlighter()

    for tag_name, color in highlighter_ref[0].colors.items():
        text_editor.tag_config(tag_name, foreground=color)

    highlight_all()  # re-highlight

explanation = ctk.CTkLabel(debugging_frame, text=f"Select a Syntax Highlighter for the Current File",
                            font=("Segoe UI",12), text_color=number_col)
explanation.pack(anchor="nw",pady=(8,8))

combo_syntax_chooser = ctk.CTkComboBox(debugging_frame,
                                        values=["Python","C","C++",
                                                "Java","JavaScript",
                                                "Rust","HTML","C Sharp",
                                                "PHP"],
                                        font=("Segoe UI",12),
                                        command=lambda value: choose_current_syntax(value))
combo_syntax_chooser.pack(anchor="nw",pady=(0,8))
combo_syntax_chooser.set('Python')