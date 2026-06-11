module ddocs.manual;

import std.stdio;
import std.string;
import std.process;
import core.stdc.stdlib;

import menubar;

string available_commands = q{ALL AVAILABLE COMMANDS:
GENERAL: clear, exit, help, version
TOOLS  : list, search <name>, install <name>, remove <name>, update <name>, info <name>};

enum RESET   = "\x1b[0m" ;
enum RED     = "\x1b[31m";
enum GREEN   = "\x1b[32m";
enum YELLOW  = "\x1b[33m";
enum BLUE    = "\x1b[34m";

void writeWelcome()
{
    writeln("Welcome to DreamStudio's Utility Manager TUI");
    writeln("Manage your developer tools from the terminal");
    writeln("Type 'help' to see available commands, or 'list' to browse tools");
}

void parseUserInput(string arg)
{
    arg = arg.strip;
    if (arg.length == 0) return;

    auto space_idx = arg.indexOf(' ');
    string user_command = (space_idx != -1) ? arg[0 .. space_idx] : arg;
    string param = (space_idx != -1) ? arg[space_idx + 1 .. $].strip : "";

    if (user_command == "clear")
    {
        version (Windows)
            spawnShell("cls").wait;
        else
            spawnShell("clear").wait;

        drawBar("DREAMSTUDIO UTILITY MANAGER");
        drawCustomPanel();
        writeWelcome();
    }
    else if (user_command == "exit")
    {
        writeln("Goodbye!");
        exit(0);
    }
    else if (user_command == "help")
    {
        writeln(available_commands);
    }
    else if (user_command == "version")
    {
        writeln("DreamStudio Utility Manager v1.0.0");
    }
    else if (user_command == "list")
    {
        writeln(GREEN, "Available tools:", RESET);
        writeln("  [installed]  dmd       - D compiler");
        writeln("  [installed]  dub       - D package manager");
        writeln("  [available]  dfmt      - D code formatter");
        writeln("  [available]  dscanner  - D static analyzer");
        writeln("  [available]  dcd       - D completion daemon");
    }
    else if (user_command == "search")
    {
        if (param.length == 0)
        {
            writeln(RED, "Usage: search <tool-name>", RESET);
            return;
        }
        writeln(YELLOW, "Searching for '", param, "'...", RESET);
        writeln("  '", param, "' is available for installation");
    }
    else if (user_command == "install")
    {
        if (param.length == 0)
        {
            writeln(RED, "Usage: install <tool-name>", RESET);
            return;
        }
        write(BLUE, "Installing '", param, "'...", RESET);
        writeln(GREEN, " done!", RESET);
    }
    else if (user_command == "remove")
    {
        if (param.length == 0)
        {
            writeln(RED, "Usage: remove <tool-name>", RESET);
            return;
        }
        write(YELLOW, "Removing '", param, "'...", RESET);
        writeln(GREEN, " done!", RESET);
    }
    else if (user_command == "update")
    {
        if (param.length == 0)
        {
            writeln(RED, "Usage: update <tool-name>", RESET);
            return;
        }
        write(BLUE, "Updating '", param, "'...", RESET);
        writeln(GREEN, " done!", RESET);
    }
    else if (user_command == "info")
    {
        if (param.length == 0)
        {
            writeln(RED, "Usage: info <tool-name>", RESET);
            return;
        }
        writeln(YELLOW, "Tool: ", param, RESET);
        writeln("  Description: Developer utility for DreamStudio");
        writeln("  Version: 1.0.0");
        writeln("  Status: available");
    }
    else
    {
        writeln(RED, "Unknown command: '", user_command, "'", RESET);
        writeln("Type 'help' to see available commands");
    }
}

void main()
{
    try
    {
        version (Windows)
            spawnShell("cls").wait;
        else
            spawnShell("clear").wait;
    }
    catch (ProcessException e)
    {
        writeln("Error occurred: ", e);
    }

    drawBar("COPYRIGHT 2026 DREAMSTUDIO UTILITY MANAGER - ALL RIGHTS RESERVED");
    drawCustomPanel();
    writeWelcome();
    while (true)
    {
        write("DSUTILS>>> ");
        string user_input = readln();
        if (user_input.length == 0) continue;
        parseUserInput(user_input);
    }
}
