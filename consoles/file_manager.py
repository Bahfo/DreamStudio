import customtkinter as ctk
import os, threading, shutil, psutil


ctk.set_appearance_mode('dark')
ctk.set_default_color_theme('dark-blue')

import os
import customtkinter as ctk

class Terminal:
    def __init__(self):
        self.window = ctk.CTk()
        self.window.title("Command Window")
        self.window.iconbitmap(r"icons\system\terminal.ico")
        self.window.geometry('830x450')

        self.help_tool = """
            ─────────────────────────────────────────────────────────────────────
                     DREAMSTUDIOS — DEVELOPER 
                                    © EX Technologies
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

        self.all_commands = """ALL SHELL COMMANDS
            ─────────────────────────────────────────────────────────────────────
            FILE AND WORKSPACE MANAGEMENT
            ─────────────────────────────────────────────────────────────────────
            copyfile                Copies a file from source to destination
            movefile                Moves a file from source to destination
            dispfirstlines          Displays first few lines of a file
            displastlines           Displays last few lines of a file
            rename                  Renames a file
            countfiles              Counts words, chars, and lines in a file
            dispcontent             Displays the content of a file
            addfile                 Makes a new file
            deletefile              Deletes a selected file
            appendfile              Appends the file in a sepcified line by a text
            makeworkspace           Makes a new workspace
            deleteworkspace         Deletes a current workspace
            copyworkspace           Copies a certain workspace
            moveworkspace           Moves a workspace from source to destination
            list                    List all files inside a workspace
            findpath                Finds the path of a folder or a file in the 
                                    current workspace listed
            changeworkspace         Changes the workspace directory
            changepermissions       Changes permissions for a file
            changeowner             Changes the owner of the file
            filestatus              Lists the status of a file
            folderstatus            Lists the status of a folder
            ─────────────────────────────────────────────────────────────────────
            SYSTEM AND ENVIRONMENT
            ─────────────────────────────────────────────────────────────────────
            isactive                Shows if a process is active or not by name
            sysinfo                 Shows general system info
            diskinfo                Shows disk info
            meminfo                 Shows memory info
            cpuinfo                 Shows CPU info
            listenv                 Lists environment variables
            setenv                  Sets a new environment variable
            getenv                  Edits an environment variable
            ─────────────────────────────────────────────────────────────────────
            NETWORKING AND REMOTE
            ─────────────────────────────────────────────────────────────────────
            pinghost                Pings a host
            checkport               Checks if a port is open
            downloadfile            Downloads a file from URL
            uploadfile              Uploads a file to the server
            curl                    Fetches HTTP content
            traceroute              Traces the network  
            ─────────────────────────────────────────────────────────────────────
            SCRIPTING AND EXECUTION
            ─────────────────────────────────────────────────────────────────────
            runpy                   Runs a Python file
            runsh                   Runs a shell file
            compile                 Compiles a file
            runbatch                Runs a batch file
            ─────────────────────────────────────────────────────────────────────
            TERMINAL
            ─────────────────────────────────────────────────────────────────────
            typemessage             Shows a message into the screen
            help                    Shows help
            showcommands            Current: Shows terminal commands
            clear                   Clears the screen
            exit                    Exits the terminal
            """

        self.error_0 = "bad command, perhaps you check list of commands? type showcommands"
        self.error_1 = """\nCheck:\n 1.The correct path\n 2.Add the extension if missing \n 
            3. Perhaps you didn't specify the language correctly?\n
            Check the documentation or type (help) for help"""


        # ---------------------- Terminal Textbox ----------------------
        self.terminal_textbox = ctk.CTkTextbox(self.window, fg_color="#1d1d1d", corner_radius=0, wrap="word",
                                               font=("Consolas", 14))
        self.terminal_textbox.insert("0.0", "DreamStudio Command Windows \nCOPYRIGHT 2026 EX Technologies\n")
        self.terminal_textbox.pack(padx=(5,5), pady=(5,5), fill='both', side='left', expand=True)
        self.terminal_textbox.configure(state="normal")

        # ---------------------- History ----------------------
        self.list_of_commands = []
        self.history_index = 0

        # ---------------------- Bindings ----------------------
        self.terminal_textbox.bind("<Key>", self.on_key)
        self.terminal_textbox.bind("<Return>", self.on_enter)
        self.terminal_textbox.bind("<Up>", self.up_arrow)
        self.terminal_textbox.bind("<Down>", self.down_arrow)
        self.terminal_textbox.bind("<Control-c>", self.ctrl_c)

        self.insert_prompt()
        

    def insert_prompt(self):
        self.terminal_textbox.configure(state="normal")
        self.terminal_textbox.insert(ctk.END, f"{os.getcwd()}>>> ")
        self.editable_index = self.terminal_textbox.index("end-1c")
        self.terminal_textbox.mark_set("insert", self.editable_index)
        self.terminal_textbox.see(ctk.END)
        self.history_index = 0  # reset history navigation

    def up_arrow(self, event):
        if not self.list_of_commands:
            return "break"
        if self.history_index < len(self.list_of_commands):
            self.history_index += 1
            cmd = self.list_of_commands[-self.history_index]
            self.terminal_textbox.delete(self.editable_index, ctk.END)
            self.terminal_textbox.insert(ctk.END, cmd)
        return "break"

    def down_arrow(self, event):
        if not self.list_of_commands:
            return "break"
        if self.history_index > 1:
            self.history_index -= 1
            cmd = self.list_of_commands[-self.history_index]
            self.terminal_textbox.delete(self.editable_index, ctk.END)
            self.terminal_textbox.insert(ctk.END, cmd)
        elif self.history_index == 1:
            self.history_index -= 1
            self.terminal_textbox.delete(self.editable_index, ctk.END)
        return "break"

    def ctrl_c(self, event):
        self.terminal_textbox.insert(ctk.END, "^C\n")
        self.insert_prompt()
        return "break"

    def on_enter(self,event=None):
        text = self.terminal_textbox.get(self.editable_index, "end-1c")
        self.terminal_textbox.insert(ctk.END, "\n")
        self.list_of_commands.append(text)

        threading.Thread(target = self.command_execution, 
                         args=(text, self.terminal_textbox), daemon=True).start()
        self.insert_prompt()
        return "break"

    def on_key(self, event=None):
        if self.terminal_textbox.compare("insert", "<", self.editable_index):
            self.terminal_textbox.mark_set("insert", self.editable_index)
        if event.keysym in ("BackSpace", "Delete"):
            if self.terminal_textbox.compare("insert", "<=", self.editable_index):
                return "break"

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

                            user_input = self.terminal_textbox.get("end-2c linestart", "end-1c").strip().lower()
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
                start_index = self.terminal_textbox.index("end-2c linestart")
                end_index = self.terminal_textbox.index("end-2c lineend")
                self.terminal_textbox.tag_config("message_line", foreground="#ffc898")
                self.terminal_textbox.tag_add("message_line", start_index, end_index)
            
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
                self.window.destroy()

            # CLEAR SCREEN
            elif command_identifier == 'clear':
                screen_widget.delete('0.0','end')
                screen_widget.insert("0.0","DreamStudio Command Window \nCOPYRIGHT 2026 EX Technologies"+'\n')

            elif command_identifier == 'history':
                screen_widget.insert(ctk.END,"History of Commands: \n" + "\n".join(self.list_of_commands) + '\n')

            else:
                screen_widget.insert(ctk.END, f"{self.error_0}\n")
                pass
        
        self.insert_prompt()
        screen_widget.see(ctk.END)

    def run(self):
        self.window.mainloop()

if __name__ == '__main__':
    cmd = Terminal()
    cmd.run()