module shells.file_manager.file_manager;

/** 
 * COPYRIGHT 2026 DREAMSTUDIO DEVELOPER TERMINAL
 * A CUSTOM TERMINAL FOR DEBUGGING PROJECT'S SCRIPTS
 * THIS SCRIPT IS NOT A PART OF PUBLISHMENT NOR COPY
 * UNDER THE GENERAL AGREEMENT OF DEVELOPERS WORKING
 * WITH DREAMSTUDIO'S ENVIRONMENT.

 * Written By Bahaa Nofal - 15/2/2026
*/

import std.path;
import std.file;
import std.stdio;
import std.string;
import std.format;
import std.process;
import std.exception;

import std.algorithm.searching;

import std.exception : assumeWontThrow;


void showAllCommands()
{
    string allCommands = q{All commands: 
Delete-Cache                Deletes all cached files or folders specified by the user recursively
                            in one directory and its subdirectories
};
    writeln(allCommands);
}

void deleteCachedData(string directory, string cacheName, bool showHelp)
{
    if (showHelp)
    {
        writeln(q{
USAGE:
    Deletes all cached data (files or folders) specified by the user
    recursively in one directory and its subdirectories.

SYNTAX:
    Delete-Cache <Directory> <Cache Name> <FLAGS>

        Directory:   Directory path
        Cache Name:  Name of the file or folder to clean
        FLAGS:
            -h / --help    Generating Help

MORE DETAILS:
    Read DreamStudio documentation.
});
        return;
    }

    if (!directory)
    {
        directory = getcwd();
    }

    foreach (entry; dirEntries(directory, SpanMode.depth))
    {
        if (baseName(entry.name) == cacheName)
        {
            writeln("Deleting: ", entry.name);

            if (entry.isDir)
            {
                rmdirRecurse(entry.name);
            }
            else
            {
                remove(entry.name);
            }
        }
    }
}

void handleUserInput(string rawCommand)
{
    string[] tokens = rawCommand.split();

    if (tokens[0] == "clear" || tokens[0] == "cls")
    {
        spawnShell("cls").wait;
    }

    if (tokens[0] == "showCommands" || tokens[0] == "commands")
    {
        showAllCommands();
    }

    if (tokens[0] == "Delete-Cache")
    {
        if (canFind(tokens, "-h") || canFind(tokens, "--help"))
        {
            deleteCachedData("", "", true);
        }
        else
        {
            deleteCachedData(tokens[1], tokens[2], false);
        }
    }
}

void main()
{
    while (true)
    {
        string currendDirectory = getcwd();
        writef("%s> ",currendDirectory);
        string userInput = readln();
        handleUserInput(userInput);
    }
}