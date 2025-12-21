help_tool = """
─────────────────────────────────────────────────────────────────────────────────────
                    DREAMSTUDIO IDE — CYBERSECURITY DEVELOPERS KIT
                                © EX Technologies
─────────────────────────────────────────────────────────────────────────────────────

DESCRIPTION:

A terminal-based development/cybersecurity kit for developers and
ethical hackers. It provides:
• Basic File and Directory Management.
• Network Scanning and Recon.
• Packet Capture and Analysis.
• Vulnerability and Exploitation.
• Password Cracking and Brute Force.
• Wireless Wi-Fi Tools.
• OSINT and Recon Tools.

─────────────────────────────────────────────────────────────────────────────────────
COMMAND INDEX:
• Display all available commands:          showcommands
• Display help documentation:              help
• Exit terminal environment:               exit

─────────────────────────────────────────────────────────────────────────────────────
NOTE:
All command inputs are processed sequentially by the terminal's
core interpreter. Invalid or malformed syntax may result in
undefined behavior or ignored operations.
─────────────────────────────────────────────────────────────────────────────────────
END OF DOCUMENTATION
"""

all_commands = """ALL SHELL COMMANDS
─────────────────────────────────────────────────────────────────────────────────────
FILE AND WORKSPACE MANAGEMENT
─────────────────────────────────────────────────────────────────────────────────────
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
─────────────────────────────────────────────────────────────────────────────────────
SYSTEM AND ENVIRONMENT
─────────────────────────────────────────────────────────────────────────────────────
isactive                Shows if a process is active or not by name
sysinfo                 Shows general system info
diskinfo                Shows disk info
meminfo                 Shows memory info
cpuinfo                 Shows CPU info
─────────────────────────────────────────────────────────────────────────────────────
NETWORKING AND REMOTE
─────────────────────────────────────────────────────────────────────────────────────
pinghost                Pings a specified host to check connectivity
traceroute              Shows the route packets take to a host
portscan                Scans a host for open ports
massscan                Performs a fast port scan across multiple hosts
checkservices           Lists services running on specified ports
resolvehostname         Resolves IP addresses to hostnames
resolveip               Resolves hostnames to IP addresses
whoisquery              Performs a WHOIS lookup on a domain or IP
dnslookup               Queries DNS records for a domain
arpcheck                Lists ARP table entries on the network
networkinfo             Displays network interfaces and IP configuration
subnetcalc              Calculates subnet details from IP and mask
checkconnections        Lists active network connections
─────────────────────────────────────────────────────────────────────────────────────
PACKET CAPTURE AND ANALYSIS
─────────────────────────────────────────────────────────────────────────────────────
capturepackets          Captures network packets on a selected interface
displaypackets          Displays captured packets in readable format
filterpackets           Filters captured packets by protocol, IP, or port
savecapture             Saves captured packets to a file
loadcapture             Loads a previously saved capture file
analyzepackets          Analyzes packet content for anomalies or patterns
extractpayload          Extracts payload data from packets
followstream            Follows TCP/UDP streams for session analysis
decodeprotocols         Decodes common protocols (HTTP, DNS, SMTP, etc.)
checktraffic            Summarizes traffic statistics per protocol
monitorinterface        Monitors a network interface in real-time
exporttocsv             Exports packet details to CSV for analysis
alertonpattern          Alerts when a specified packet pattern is detected
─────────────────────────────────────────────────────────────────────────────────────
VULNERABILITY AND EXPLOITATION
─────────────────────────────────────────────────────────────────────────────────────
scanvulnerabilities      Scans a host or network for known vulnerabilities
checkssl                 Checks SSL/TLS configuration and certificate
                            validity
scanweb                  Scans a website for common security issues
sqlinjecttest            Tests a website for SQL injection vulnerabilities
xsscheck                 Tests a website for Cross-Site Scripting (XSS) 
                            vulnerabilities
directorybruteforce      Performs directory and file brute-force enumeration
checkports               Lists open ports that may be vulnerable
exploittarget            Attempts to exploit a known vulnerability on a host
checkpatches             Checks if software patches are missing
enumerateusers           Enumerates users on a target system
checkconfig              Checks misconfigurations in servers or services
reportvulnerabilities    Generates a vulnerability report for a target
updateexploitdb          Updates the local exploit database
─────────────────────────────────────────────────────────────────────────────────────
TERMINAL
─────────────────────────────────────────────────────────────────────────────────────
typemessage             Shows a message into the screen
help                    Shows help
showcommands            Current: Shows terminal commands
clear                   Clears the screen
exit                    Exits the terminal
"""

import customtkinter as ctk
import cmd
import sys
import os
import re

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

variables = {}

class stdout:
    def __init__(self, textbox):
        self.textbox = textbox

    def write(self, text):
        if text.strip():
            self.textbox.insert("end", "\n" + text, "output")
            self.textbox.see("end")

    def flush(self):
        pass

class Terminal:
    def __init__(self):
        self.window = ctk.CTk()
        self.window.title("Cybersecurity Developer's Command Window")
        self.window.iconbitmap(r"icons\system\terminal.ico")
        self.window.geometry("830x450")

        # ---------------------- Terminal Textbox ----------------------
        self.terminal_textbox = ctk.CTkTextbox(
            self.window,
            fg_color="#1d1d1d",
            corner_radius=0,
            wrap="word",
            font=("Consolas", 14))
        self.cmd_shell = cmdCommands(stdout=stdout(self.terminal_textbox))

        self.terminal_textbox.pack(
            padx=5, pady=5, fill="both", expand=True)

        self.terminal_textbox.insert(
            "0.0", "DreamStudio Cybersecurity Developer's Kit \nCOPYRIGHT 2026 EX Technologies\n")
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
        self.history_index = 0 # RESET

    def up_arrow(self, event):
        if not self.list_of_commands:
            return "break"
        if self.history_index < len(self.list_of_commands):
            self.history_index += 1
            cmd = self.list_of_commands[-self.history_index]
            self.terminal_textbox.delete(self.editable_index, ctk.END)
            self.terminal_textbox.insert(ctk.END, cmd)
            self.terminal_textbox.mark_set("insert", ctk.END)
        return "break"

    def down_arrow(self, event):
        if not self.list_of_commands:
            return "break"
        if self.history_index > 1:
            self.history_index -= 1
            cmd = self.list_of_commands[-self.history_index]
            self.terminal_textbox.delete(self.editable_index, ctk.END)
            self.terminal_textbox.insert(ctk.END, cmd)
            self.terminal_textbox.mark_set("insert", ctk.END)
        elif self.history_index == 1:
            self.history_index -= 1
            self.terminal_textbox.delete(self.editable_index, ctk.END)
            self.terminal_textbox.mark_set("insert", ctk.END)
        return "break"

    def ctrl_c(self, event):
        self.terminal_textbox.insert(ctk.END, "^C\n")
        self.insert_prompt()
        return "break"

    def on_enter(self, event=None):

        text = self.terminal_textbox.get(self.editable_index, "end-1c").strip()
        self.terminal_textbox.insert(ctk.END, "\n")
        if text:
            self.list_of_commands.append(text)
            self.cmd_shell.onecmd(text)
        self.insert_prompt()
        return "break"

    def on_key(self, event=None):
        # Prevent typing above the prompt
        if self.terminal_textbox.compare("insert", "<", self.editable_index):
            self.terminal_textbox.mark_set("insert", self.editable_index)
        # Prevent deleting the prompt
        if event.keysym in ("BackSpace", "Delete"):
            if self.terminal_textbox.compare("insert", "<=", self.editable_index):
                return "break"

    def run(self):
        self.window.mainloop()

class cmdCommands(cmd.Cmd):
    def __init__(self, stdout=None):
        super().__init__(stdout=stdout)
        self.currentDir = os.getcwd()
        self.prompt = f"{self.currentDir}>>> "
        self._history_index = None
        self.commandsList = {
            "copyfile",
            "movefile",
            "dispfirstlines",
            "displastlines",
            "rename",
            "countfiles",
            "dispcontent",
            "addfile",
            "deletefile",
            "appendfile",
            "makeworkspace",
            "deleteworkspace",
            "copyworkspace",
            "moveworkspace",
            "list",
            "findpath",
            "changeworkspace",
            "changepermissions",
            "changeowner",
            "filestatus",
            "folderstatus",
            "isactive",
            "sysinfo",
            "diskinfo",
            "meminfo",
            "cpuinfo",
            "pinghost",
            "traceroute",
            "portscan",
            "massscan",
            "checkservices",
            "resolvehostname",
            "resolveip",
            "whoisquery",
            "dnslookup",
            "arpcheck",
            "networkinfo",
            "subnetcalc",
            "checkconnections",
            "capturepackets",
            "displaypackets",
            "filterpackets",
            "savecapture",
            "loadcapture",
            "analyzepackets",
            "extractpayload",
            "followstream",
            "decodeprotocols",
            "checktraffic",
            "monitorinterface",
            "exporttocsv",
            "alertonpattern",
            "scanvulnerabilities",
            "checkssl",
            "scanweb",
            "sqlinjecttest",
            "xsscheck",
            "directorybruteforce",
            "checkports",
            "exploittarget",
            "checkpatches",
            "enumerateusers",
            "checkconfig",
            "reportvulnerabilities",
            "updateexploitdb",
            "typemessage",
            "help",
            "showcommands",
            "clear",
            "exit"}

    def parse_args(self, arg:str):
        parts = arg.split()
        args = {}
        for p in parts:
            if "=" in p:
                if p.startswith("-"):
                    """
                    This is a normal parameter. Save as it is
                    """
                    key, value = p.split("=")
                    key = key.removeprefix("--").removeprefix("-")
                    value = value.removeprefix(" ").strip("'").strip('"')
                    args[key] = value
                elif p.startswith("$"):
                    """
                    This is a variable. Append to a dictionary
                    """
                    if "=" in p:
                        var_name, var_value = p.split("=")
                        if var_name and (var_name.startswith(tuple["1234567890"]) or var_name == n for n in self.commandsList):
                            return "Naming Error: Could not name a variable starting with a number"
                        elif (m in var_value for m in ["!","@","#","$","%","^","&","*","(",")","-","+","="]):
                            return f"Assigning Error: Cannot assign the specified value into variable {var_name}"
                        else:
                            variables[var_name] = var_value
                            return f"variable {var_name} saved"
                elif p.startswith("%"):
                    """
                    Comments. Ignore
                    """
                    parts.pop(p)

    def onecmd(self, line):
        line = line.strip()
        if line:
            return super().onecmd(line)

    def do_help(self, arg):
        """
        NAME:
            help 
        SYNTAX:
            help -arg
        PARAMETERS:
            -arg: Name of a command, unit, function, method, etc.
        DESCRIPTION:
            <help> is designed to generate documented help within the terminal
            about a specific topic. Users can type in the command's name and an 
            auto-help will be generated about the command specified. There is 
            also documentation about topics. The user can type in the topic name
            and some help can be generated.
        FEATURES:
        OUTPUT:
        ERRORS:
        HOT-COMMANDS:
            <showcommands> <clear> <exit> <get_doc>
        """
        if arg != "":
            return super().do_help(arg)
        else:
            return help_tool

    def do_copyfile(self, arg):
        """
        Help: copyfile: Copies a file from specified source to destination
        Parameters:
        -src/--source:  source path, default is current working directory if file is found
        -dest/--destination: destination path, must be specified
        -file name: if source not specified
        Optional Parameters:  
        -f/--force: force copying the file 
        -r/--rec: recursively copies the file
        """        

        # if re.search(source_path,f'{os.getcwd()}'):
        #     if (source_path == os.getcwd()):
        #         source_path + rf'\{file_name}'

if __name__ == "__main__":
    cmd = Terminal()
    cmd.run()
