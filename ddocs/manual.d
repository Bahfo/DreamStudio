module ddocs.manual;

import std.uni;
import std.file;
import std.path;
import std.stdio;
import std.string;
import std.process;
import std.datetime;
import std.exception;

import std.algorithm : any;

import core.stdc.stdlib;

string available_commands = q{ALL AVAILABLE COMMANDS:
GENERAL      : clear, exit, help
GET FAMILY   : get-started, get-commands
SEARCH FAMILY: search-topic, search-several
OPEN FAMILY  : open-pdf, open-web};

enum RESET   = "\x1b[0m" ;
enum RED     = "\x1b[31m";
enum GREEN   = "\x1b[32m";
enum YELLOW  = "\x1b[33m";
enum BLUE    = "\x1b[34m";

string checkVersion()
{
    version(Windows) return "windows";
    version(linux)   return "linux";
    version(OSX)     return "macos";
}

void openPDF(string filePath)
{
    string command;

    version (Windows)
    {
        command = `cmd /c start "" "` ~ filePath ~ `"`;
    }
    else version (OSX)
    {
        command = `open "` ~ filePath ~ `"`;
    }
    else version (Unix)
    {
        command = `xdg-open "` ~ filePath ~ `"`;
    }
    else
    {
        writeln("Opening PDF not supported on this OS.");
        return;
    }

    auto exitCode = executeShell(command);
    if (exitCode.status != 0)
    {
        writeln("Failed to open documentation. Unknown exception occurred");
    }
}

void searchTopic(string rootDir, string topicWord) {

    void searchDir(string dir)
    {
        foreach (entry; dirEntries(dir, SpanMode.shallow))
        {
            if (entry.name.indexOf(topicWord) >= 0)
            {
                writeln("Found in name: ", entry.name);
            }
            if (entry.isDir)
            {
                searchDir(entry.name);
            }
            else if (entry.isFile)
            {
                try
                {
                    auto content = readText(entry.name);
                    if (content.indexOf(topicWord) >= 0)
                    {
                        writeln("Found in file: ", entry.name);
                    }
                }
                catch (Exception e)
                {
                    writeln("Error: Could not find file needed: ",e);
                }
            }
        }
    }
    searchDir(rootDir);
}

void writeWelcome()
{
    writeln("Welcome to DreamStudio's Terminal Documentation DDocs");
    writeln("Please enter the name of the topic you are looking for");
    writeln("For starting up, read 'welcome' by typing 'get-started'");
}

void parseUserInput(string arg)
{
    //CHECKING FOR OPERATING SYSTEM VERSION FOR BETTER COMPATABILITY
    string version_type = checkVersion();
    // PARSING USER COMMAND BASED ON ITS IDENTIFIERS AND TYPE
    arg = arg[0 .. $].strip;  // Just for ensuring we take full line
    auto space_idx = arg.indexOf(' ');
    auto dash_idx = arg.indexOf('-');
    string user_command = (space_idx != -1) ? arg[0 .. space_idx] : arg;
    string search_param = (space_idx != -1) ? arg[space_idx + 1 .. $] : arg;
    string command_identifier;
    string command_type;
    if(dash_idx != -1)
    {
        command_identifier = user_command[0 .. dash_idx];
        command_type = user_command[dash_idx + 1 .. $];
    }

    // MATCHING COMMAND TYPE WITH COMMAND IDENTIFIER
    if (user_command == "clear")
    {
        if (version_type == "windows") {spawnShell("cls").wait; writeWelcome();}
        if (version_type == "linux" || version_type == "macos")
            {spawnShell("clear").wait; writeWelcome();}
    }
    else if (user_command == "exit")
    {
        exit(0);
    }
    else if (user_command == "help")
    {
        string help_content = cast(string) readText("./docs/help.dsman");
        writeln(help_content);
    }

    else
    {
        if (toLower(command_identifier) == "get" &&
        toLower(command_type) == "started")
        {
            string contents = cast(string) readText("./docs/get_started.dsman");
            writeln(contents);
        }

        else if(toLower(command_identifier) == "get" &&
        toLower(command_type) == "commands")
        {
            writeln(available_commands);
        }

        else if (toLower(command_identifier) == "search" &&
        toLower(command_type == "topic"))
        {
            searchTopic("./docs", search_param);
        }

        else if (toLower(command_identifier) == "open" &&
        toLower(command_type) == "pdf")
        {
            openPDF("./docs/manual.pdf");
        }
        else
        {
            writeln("Unknown command: Please type-in the correct command");
            writeln("or type 'get-commands' to see full commands list");
        }
    }
}

void colorizeInputs(string arg)
{
    string[] keywords = ["get-commands","get-started","open-web","help",
                         "open-pdf","search-topic","search-several"];

    auto words = arg.split(' ');
    foreach (string word; words)
    {
        bool matched = keywords.any!(k=> word.toLower().startsWith(k.toLower()));

        if (matched)
        {
            writeln(YELLOW,">>> COMMAND: ", word, RESET, " ");
        }
    }
}

// string lookInsideDocs(string parsed_input)
// {
//     return;
// }

void main()
{
    version(Windows)
        {
            try
            {
                spawnShell("cls").wait;
            } catch (ProcessException e)
            {
                writeln("Error Occured: ", e);
            }
        }

    writeWelcome();
    while(true)
    {
        write("> ");
        string user_input = readln();
        writeln("");
        colorizeInputs(user_input);
        parseUserInput(user_input);
    }
}
