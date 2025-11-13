import customtkinter as ctk
import os, threading, shutil, psutil

def main_terminal():

    ctk.set_appearance_mode('dark')
    ctk.set_default_color_theme('dark-blue')

    def center_window(window):
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        window.geometry(f"{width}x{height}+{x}+{y}")

    window = ctk.CTk()
    window.title("daydream terminal")
    # window.iconbitmap(r"icons\terminal.ico")
    window.eval('tk::PlaceWindow . center')
    center_window(window)
    window.geometry('830x450')

    ###########################################################################################
    # TEXTBOX
    ###########################################################################################
    terminal_textbox = ctk.CTkTextbox(window,bg_color="#2e2e2e",corner_radius=0,wrap="word",
                                      font=("Consolas",16))
    terminal_textbox.insert("0.0","Daydream Console \nCOPYRIGHT 2026 EX Technologies"+'\n')
    terminal_textbox.pack(padx=(5,5),pady=(5,5),fill='both',side='left',expand=True)
    terminal_textbox.configure(state="normal")

    terminal_textbox.tag_config("command", foreground="#f5ff98")
    terminal_textbox.tag_config("parameter", foreground="#a7ff98")
    terminal_textbox.tag_config("language", foreground="#98d8ff")
    terminal_textbox.tag_config("word", foreground= "#ffe598")
    terminal_textbox.tag_config("number", foreground= "#ff98f3")
    terminal_textbox.tag_config("subcommand", foreground= "#ff9898")
    terminal_textbox.tag_config("special_parameters", foreground= "#bc98ff")

    def insert_prompt():
        global editable_index
        terminal_textbox.insert(ctk.END, ">>> ")  # prompt
        editable_index = terminal_textbox.index("end-1c")  # start of editable region
        terminal_textbox.see(ctk.END)

    insert_prompt()

    class BasicMode():

        def __init__(self):

            self.help_tool = """
            ─────────────────────────────────────────────────────────────────────
                     SOFTDREAM IDE — FILE MANAGEMENT INDEPENDENT SYSTEM
                                   © EX Technologies Ltd.
            ─────────────────────────────────────────────────────────────────────

            DESCRIPTION:

            This terminal offers secure execution of essential instructions
            concerning:
            • File and directory management.
            • Workspace organization and maintenance routines.

            ────────────────────────────────────────────────────────────────────
            COMMAND INDEX:
            • Display all available commands:          showcommands
            • Display help documentation:              help
            • Exit terminal environment:               exit

            ────────────────────────────────────────────────────────────────────
            NOTE:
            All command inputs are processed sequentially by the terminal's
            core interpreter. Invalid or malformed syntax may result in
            undefined behavior or ignored operations.
            ────────────────────────────────────────────────────────────────────
            END OF DOCUMENTATION

            """

            self.all_commands = """
            BASIC MODE COMMANDS:
            copyfile          file_name      source_path      destination_path
            movefile          file_name      source_path      destination_path
            dispfirstlines    file_name      file_path        number_of_lines
            displastlines     file_name      file_path        number_of_lines
            rename            file_name      file_path        new_name
            countfiles        file_name      file_path        sum_type
                sum_type PARAMETERS:
                wordsum:   sum of words
                charsumsp: chars sum without spaces
                charsum:   chars sum with spaces
                linesum:   lines sum
            dispcontent       file_name      file_path
            addfile           file_name      file_path
            deletefile        file_name      file_path
            makeworkspace     make_name      make_path
            deleteworkspace   make_name      make_path
            list              make_name      make_path
            findpath          root_dir       search_name
            isactive          file_name
            typemessage       message
            help
            showcommands
            clear
            exit
            """

            self.error_0 = "bad command, perhaps you check list of commands? type showcommands"
            self.error_1 = """\nCheck:\n 1.The correct path\n 2.Add the extension if missing \n 
            3. Perhaps you didn't specify the language correctly?\n
            Check the documentation or type (help) for help"""

        def command_execution(self,user_input,screen_widget):
            user_input = user_input.lower()
            parts = user_input.split()
            command_identifier = parts[0]

            if len(parts) == 4:
                parameter_1 = parts[1]          # Name
                parameter_2 = parts[2]          # Path
                parameter_3 = parts[3]          # Source Language / Or Destination Path / Or number of lines to display
                
                # DISPLAY FIRST LINES
                if command_identifier == 'dispfirstlines':
                    full_path = os.path.join(parameter_2, parameter_1)

                    if not os.path.exists(full_path):
                        screen_widget.insert(ctk.END, f"File '{parameter_1}' not found in '{parameter_2}' {self.error_1}\n")
                    else:
                        try:
                            file = open(f"{full_path}","r")
                            contents = file.readlines()
                            lines_to_read = contents[0:int(parameter_3)]
                            screen_widget.insert(ctk.END, lines_to_read)
                        except Exception as e:
                            screen_widget.insert(ctk.END, f"Error showing file contents: {e}\n")

                # DISPLAY LAST LINES
                elif command_identifier == 'displastlines':
                    full_path = os.path.join(parameter_2,parameter_1)
                    if not os.path.exists(full_path):
                        screen_widget.insert(ctk.END, f"File '{parameter_1}' not found in '{parameter_2}' {self.error_1}\n")
                    else:
                        try:
                            with open(f"{full_path}","r") as file:
                                contents = file.readlines()
                                number_of_lines = len(contents) - int(parameter_3)
                                lines_to_read = contents[number_of_lines:len(contents)]
                                screen_widget.insert(ctk.END,lines_to_read)
                        except Exception as e:
                            screen_widget.insert(ctk.END, f"Error showing file contents: {e}\n")

                # COPYFILE
                elif command_identifier == 'copyfile':
                    full_path = os.path.join(parameter_2, parameter_1)

                    if not os.path.exists(full_path):
                        screen_widget.insert(ctk.END, f"File '{parameter_1}' not found in '{parameter_2}' {self.error_1}\n")
                    else:
                        try:
                            destination_file = os.path.join(parameter_3, parameter_1)
                            shutil.copyfile(full_path, destination_file)
                            screen_widget.insert(ctk.END, f"Copied '{parameter_1}' to '{parameter_3}' successfully\n")
                        except Exception as e:
                            screen_widget.insert(ctk.END, f"Error copying file: {e}\n")

                # MOVEFILE   movefile file_name source_path destination_path
                elif command_identifier == 'movefile':
                    full_path = os.path.join(parameter_2,parameter_1)

                    if not os.path.exists(full_path):
                        screen_widget.insert(ctk.END, f"File '{parameter_1}' not found in '{parameter_2}' {self.error_1}\n")
                    else:
                        try:
                            destination_file = os.path.join(parameter_3, parameter_1)
                            shutil.move(full_path,destination_file)
                            screen_widget.insert(ctk.END, f"Moved '{parameter_1}' to '{parameter_3}' successfully\n")
                        except Exception as e:
                            screen_widget.insert(ctk.END, f"Error moving file: {e}\n")

                # RENAME
                elif command_identifier == 'rename':
                    full_path = os.path.join(parameter_2,parameter_1)
                    full_path_rename = os.path.join(parameter_2,parameter_3)
                    if not os.path.exists(full_path):
                        screen_widget.insert(ctk.END, f"File '{parameter_1}' not found in '{parameter_2}' {self.error_1}\n")
                    else:
                        try:
                            os.rename(full_path,full_path_rename)
                            screen_widget.insert(ctk.END, f"File '{parameter_1}' name is changed to '{parameter_3}'\n")
                        except Exception as e:
                            screen_widget.insert(ctk.END, f"Error: {e}\n")

                elif command_identifier == 'countfiles':
                    full_path = os.path.join(parameter_2, parameter_1)
                    if not os.path.exists(full_path):
                        screen_widget.insert(ctk.END, f"File '{parameter_1}' not found in '{parameter_2}'\n")
                    else:
                        try:
                            with open(full_path, "r", encoding="utf-8") as file:
                                content = file.read()
                            
                            if parameter_3 == 'wordsum':
                                word_count = len(content.split())
                                screen_widget.insert(ctk.END, f"Number of words in {parameter_1} is {word_count}\n")

                            elif parameter_3 == 'charsumsp':
                                char_count = len(content)
                                screen_widget.insert(ctk.END, f"Number of characters in {parameter_1} is {char_count} with spaces\n")

                            elif parameter_3 == 'charsum':
                                char_count_nosp = len(content.replace(" ", "").replace("\n", "").replace("\t", ""))
                                screen_widget.insert(ctk.END, f"Number of characters in {parameter_1} is {char_count_nosp} without spaces\n")

                            elif parameter_3 == 'linesum':
                                line_count = content.count('\n') + 1 if content else 0
                                screen_widget.insert(ctk.END, f"Number of lines in {parameter_1} is {line_count}\n")

                        except Exception as e:
                            screen_widget.insert(ctk.END, f"Error: {e}\n")
                
                else:
                    screen_widget.insert(ctk.END, f"{self.error_0}\n")
                    pass


            if len(parts) == 3:
                parameter_1 = parts[1]  # Name
                parameter_2 = parts[2]  # Path

                # DISPLAY FULL FILE CONTENTS
                if command_identifier == 'dispcontent':
                    full_path = os.path.join(parameter_2,parameter_1)
                    if not os.path.exists(full_path):
                        screen_widget.insert(ctk.END, f"File '{parameter_1}' not found in '{parameter_2}' {self.error_1}\n")
                    else:
                        try:
                            file = open(f"{full_path}","r")
                            contents = file.read()
                            screen_widget.insert(ctk.END, f"{contents}\n")
                        except Exception as e:
                            screen_widget.insert(ctk.END, f"Error showing file contents: {e}\n")

                # ADD FILE
                elif command_identifier == 'addfile':
                    try:
                        full_path_add = os.path.join(parameter_2, parameter_1)
                        os.makedirs(parameter_2, exist_ok=True)  # ensure directory exists
                        with open(full_path_add, "w") as f:
                            pass
                        screen_widget.insert(ctk.END, f"File created successfully: {full_path_add}\n")

                    except Exception as e:
                        screen_widget.insert(ctk.END, f"Error: {e}\n")

                # DELETE FILE
                elif command_identifier == 'deletefile':
                    try:
                        full_path_delete = os.path.join(parameter_2, parameter_1)
                        if os.path.exists(full_path_delete):
                            os.remove(full_path_delete)
                            screen_widget.insert(ctk.END, f"File deleted successfully: {full_path_delete}\n")
                        else:
                            screen_widget.insert(ctk.END, "File not found\n")

                    except Exception as e:
                        screen_widget.insert(ctk.END, f"Error: {e}\n")

                # MAKE WORKSPACE
                elif command_identifier == 'makeworkspace':
                    try:
                        full_path_workspace = os.path.join(parameter_2, parameter_1)
                        if os.path.exists(full_path_workspace):
                            screen_widget.insert(ctk.END, f"Workspace '{parameter_1}' already exists.\n")
                        else:
                            os.makedirs(full_path_workspace, exist_ok=True)
                            screen_widget.insert(ctk.END, f"Workspace '{parameter_1}' created successfully.\n")

                    except Exception as e:
                        screen_widget.insert(ctk.END, f"Error: {e}\n")

                # DELETE WORKSPACE
                elif command_identifier == 'deleteworkspace':
                    try:
                        full_path_delete_ws = os.path.join(parameter_2, parameter_1)
                        if not os.path.exists(full_path_delete_ws):
                            screen_widget.insert(ctk.END, "Workspace not found.\n")

                        elif os.path.isdir(full_path_delete_ws):
                            if not os.listdir(full_path_delete_ws):  # folder is empty
                                os.rmdir(full_path_delete_ws)
                                screen_widget.insert(ctk.END, "Empty workspace removed successfully.\n")
                            else:
                                screen_widget.insert(ctk.END, "Workspace not empty. Confirm deletion [Y/n]:\n")

                                user_input = terminal_textbox.get("end-2c linestart", "end-1c").strip().lower()
                                if user_input == 'y':
                                    shutil.rmtree(full_path_delete_ws)
                                    screen_widget.insert(ctk.END, f"Workspace and contents deleted: {full_path_delete_ws}\n")
                                else:
                                    screen_widget.insert(ctk.END, "Deletion canceled by user.\n")

                    except Exception as e:
                        screen_widget.insert(ctk.END, f"Error: {e}\n")

                # LIST FILES IN WORKSPACE
                elif command_identifier == 'list':
                    full_path = os.path.join(parameter_2, parameter_1)
                    if not os.path.exists(full_path):
                        screen_widget.insert(ctk.END, "Workspace not found\n")
                    else:
                        # Define a version of print_tree that writes to the GUI
                        def gui_print_tree(path, widget, indent=""):
                            widget.insert(ctk.END, f"{indent}{os.path.basename(path)}/\n")
                            try:
                                for item in os.listdir(path):
                                    full_item_path = os.path.join(path, item)
                                    if os.path.isdir(full_item_path):
                                        gui_print_tree(full_item_path, widget, indent + "    ")
                                    else:
                                        widget.insert(ctk.END, f"{indent}    {item}\n")
                            except PermissionError:
                                widget.insert(ctk.END, f"{indent}    [Permission Denied]\n")

                        gui_print_tree(full_path, screen_widget)

                # DISPLAY WORKSPACE PATH
                elif command_identifier == 'findpath':
                    try:
                        for root, dirs, files in os.walk(parameter_1):
                            if parameter_2 in files:
                                screen_widget.insert(ctk.END,os.path.join(root, parameter_2))
                            if parameter_2 in dirs:
                                screen_widget.insert(ctk.END,os.path.join(root, parameter_2))
                    except Exception as e:
                        screen_widget.insert(ctk.END, f"Error: {e}\n")

                else:
                    screen_widget.insert(ctk.END, f"{self.error_0}\n")
                    pass

            if len(parts) == 2:
                parameter = parts[1]

                # CHECKING IF A PROCESS IS ACTIVE
                if command_identifier == 'isactive':
                    try:
                        for proc in psutil.process_iter(['name']):
                            if parameter.lower() in proc.info['name'].lower():
                                screen_widget.insert(ctk.END, f"process {parameter} is active\n")
                        return screen_widget.insert(ctk.END, f"process {parameter} is not active\n")
                    except Exception as e:
                        screen_widget.insert(ctk.END, f"Error: {e}\n")

                # TYPE MESSAGE
                elif command_identifier == 'typemessage':
                    screen_widget.insert(ctk.END,f"{parameter}\n")
                    start_index = terminal_textbox.index("end-2c linestart")
                    end_index = terminal_textbox.index("end-2c lineend")
                    terminal_textbox.tag_config("message_line", foreground="#ffc898")
                    terminal_textbox.tag_add("message_line", start_index, end_index)
                
                else:
                    screen_widget.insert(ctk.END, f"{self.error_0}\n")
                    pass

            if len(parts) == 1:
                # HELP
                if command_identifier == 'help':
                    screen_widget.insert(ctk.END,self.help_tool+'\n')

                # SHOWCOMMANDS
                elif command_identifier == 'showcommands':
                    screen_widget.insert(ctk.END,self.all_commands+'\n')

                # EXIT TERMINAL
                elif command_identifier == 'exit':
                    window.destroy()

                # CLEAR SCREEN
                elif command_identifier == 'clear':
                    screen_widget.delete('0.0','end')
                    screen_widget.insert("0.0","Daydream Console \nCOPYRIGHT 2026 EX Technologies"+'\n')

                else:
                    screen_widget.insert(ctk.END, f"{self.error_0}\n")
                    pass
            
            insert_prompt()
            screen_widget.see(ctk.END)

        def on_enter(self,event=None):
            global editable_index
            text = terminal_textbox.get(editable_index, "end-1c")
            terminal_textbox.insert(ctk.END, "\n")

            threading.Thread(target = self.command_execution, args=(text, terminal_textbox), daemon=True).start()
            return "break"

        def on_key(self,event=None):
            cursor_index = terminal_textbox.index("insert")

            # Get the last line
            start_index = terminal_textbox.index("end-2c linestart")
            end_index = terminal_textbox.index("end-2c lineend")
            last_line = terminal_textbox.get(start_index, end_index)

            parts = last_line.split()
            if not parts:
                return

            color_rules = {
                "copyfile":         {1: "command"},
                "typemessage":      {1: "message"},
                "movefile":         {1: "command"},
                "dispfirstlines":   {1: "command", 4: "number"},
                "displastlines":    {1: "command", 4: "number"},
                "rename":           {1: "command", 4: "word"},
                "countfiles":       {1: "command", 4: "parameter"},
                "dispcontent":      {1: "command"},
                "addfile":          {1: "command"},
                "deletefile":       {1: "command"},
                "list":             {1: "command"},
                "findpath":         {1: "command"},
                "isactive":         {1: "command"},
                "typemessage":      {1: "command", 2: "word"},
                "help":             {1: "command"},
                "showcommands":     {1: "command"},
                "clear":            {1: "command"},
                "exit":             {1: "command"},
            }

            command_name = parts[1]

            # Only apply coloring if the command is in the rules
            if command_name in color_rules:
                rules = color_rules[command_name]
                char_pos = 0
                for i, part in enumerate(parts):
                    part_start = char_pos
                    part_end = char_pos + len(part)
                    tag_start = f"{start_index}+{part_start}c"
                    tag_end = f"{start_index}+{part_end}c"

                    if i in rules:
                        terminal_textbox.tag_add(rules[i], tag_start, tag_end)

                    # Update char_pos (+1 for the space after each part)
                    char_pos = part_end + 1

            if terminal_textbox.compare(cursor_index, "<", editable_index):
                return "break"

    basic_mode = BasicMode()
    terminal_textbox.bind("<Return>", basic_mode.on_enter)
    terminal_textbox.bind("<Key>", basic_mode.on_key)

    window.mainloop()

if __name__ == '__main__':
    main_terminal()