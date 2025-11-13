import customtkinter as ctk
import threading

# ----------------------------
# Example command data
help_tool = "This is the help message.\nUse 'showcommands' to see all commands."
all_commands = """AVAILABLE COMMANDS:
help
showcommands
exit
"""

error_0 = "Bad command, perhaps you check list of commands? type showcommands"

# ----------------------------
# Create window
window = ctk.CTk()
window.geometry("700x400")
window.title("CTk Terminal")

# ----------------------------
# Terminal textbox
terminal_textbox = ctk.CTkTextbox(window, bg_color="#2e2e2e", corner_radius=0,
                                  font=("Consolas", 16))
terminal_textbox.pack(padx=5, pady=5, fill='both', expand=True)

# Disable default editing until prompt is ready
terminal_textbox.configure(state="normal")

# ----------------------------
# Track editable start
editable_index = "1.0"

def insert_prompt():
    global editable_index
    terminal_textbox.insert(ctk.END, ">>> ")  # prompt
    editable_index = terminal_textbox.index("end-1c")  # start of editable region
    terminal_textbox.see(ctk.END)

insert_prompt()

# ----------------------------
# Command execution
def command_execution(user_input, screen_widget):
    user_input = user_input.strip().lower()
    parts = user_input.split()

    if len(parts) == 0:
        return  # empty input

    if parts[0] == 'help':
        screen_widget.insert(ctk.END, help_tool + "\n")
    elif parts[0] == 'showcommands':
        screen_widget.insert(ctk.END, all_commands + "\n")
    elif parts[0] == 'exit':
        window.destroy()
    else:
        screen_widget.insert(ctk.END, error_0 + "\n")

    insert_prompt()  # add new prompt after output
    screen_widget.see(ctk.END)  # scroll to end

# ----------------------------
# Handle Enter key
def on_enter(event=None):
    global editable_index
    # Get user input after the prompt
    text = terminal_textbox.get(editable_index, "end-1c")
    terminal_textbox.insert(ctk.END, "\n")  # move to next line

    # Run command in a separate thread
    threading.Thread(target=command_execution, args=(text, terminal_textbox), daemon=True).start()
    return "break"

# ----------------------------
# Prevent editing previous lines
def on_key(event=None):
    cursor_index = terminal_textbox.index("insert")
    if terminal_textbox.compare(cursor_index, "<", editable_index):
        return "break"  # block any editing before prompt

# ----------------------------
# Bind keys
terminal_textbox.bind("<Return>", on_enter)
terminal_textbox.bind("<Key>", on_key)

# ----------------------------
# Start GUI
window.mainloop()