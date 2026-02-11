module ddocs.manual;

import std.uni;
import std.conv;
import std.file;
import std.path;
import std.stdio;
import std.string;
import std.process;
import std.datetime;
import std.exception;

import core.thread;
import core.stdc.stdlib;
import std.algorithm : any;
import std.algorithm.searching;

import menubar;

string available_commands = q{ALL AVAILABLE COMMANDS:
GENERAL      : clear, exit, help
GET FAMILY   : get-started, get-commands
SEARCH FAMILY: search-topic, search-several
OPEN FAMILY  : open-pdf};

enum RESET   = "\x1b[0m" ;
enum RED     = "\x1b[31m";
enum GREEN   = "\x1b[32m";
enum YELLOW  = "\x1b[33m";
enum BLUE    = "\x1b[34m";

struct MatchedContent
{
    string path;
}

struct MatchedLine
{
    string path; 
    size_t lineNo;
    string line;
}

struct TopicName
{
    string topicName;
    string topicPath;
}

TopicName[] topicsNames = [
    TopicName("Introduction", "./docs/help.dsman"),
    TopicName("Installation", "./docs/help.dsman"),
];

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

void searchTopic(string rootDir, string topicWord)
{
    MatchedContent[] searchDir(string dir)
    {
        MatchedContent[] matches;

        foreach (entry; dirEntries(dir, SpanMode.shallow))
        {
            if (entry.name.indexOf(topicWord) >= 0)
            {
                writeln("Found in name: ", entry.name);
                matches ~= MatchedContent(entry.name);
            }

            if (entry.isDir)
            {
                matches ~= searchDir(entry.name);
            }
            else if (entry.isFile)
            {
                try
                {
                    auto content = toLower(readText(entry.name));
                    if (content.indexOf(toLower(topicWord)) >= 0)
                    {
                        matches ~= MatchedContent(entry.name);
                    }
                }
                catch (Exception)
                {
                    writeln("Error reading file: ", entry.name);
                }
            }
        }
        return matches;
    }

    auto matches = searchDir(rootDir);

    writeln("Topic ", topicWord, " found in ", matches.length, " files");

    foreach (i, m; matches)
    {
        writeln("[", i, "] Found in ", m.path);
    }

    if (matches.length == 0)
        return;

    writeln("Type the number of topic to open it, or type 'skip' to return");

    string response = strip(readln());

    if (response == "skip")
        return;

    try
    {
        int index = to!int(response);

        if (index < 0 || index >= matches.length)
        {
            writeln("Invalid selection.");
            return;
        }

        string content = readText(matches[index].path);
        writeln(YELLOW,"---- FILE CONTENT ----",RESET);
        writeln(content);
    }
    catch (Exception)
    {
        writeln("Invalid input.");
    }
}

void searchSeveral(string rootDir, string topicWord)
{
    MatchedLine[] searchDir(string dir)
    {
        MatchedLine[] matches;

        foreach (entry; dirEntries(dir, SpanMode.shallow))
        {
            if (entry.isDir)
            {
                matches ~= searchDir(entry.name);
            }
            else if (entry.isFile)
            {
                try
                {
                    size_t lineNumber = 0;
                    foreach (line; File(entry.name).byLine())
                    {
                        lineNumber++;
                        if (toLower(line).indexOf(toLower(topicWord)) >= 0)
                        {
                            matches ~= MatchedLine(entry.name, lineNumber, line.idup);
                        }
                    }
                }
                catch (Exception)
                {
                    writeln("Error reading file: ", entry.name);
                }
            }
        }

        return matches;
    }

    auto matches = searchDir(rootDir);

    writeln("Topic '", topicWord, "' found in ", matches.length, " lines");

    foreach (i, m; matches)
    {
        writeln("[", i, "] ", m.path, " (line ", m.lineNo, "): ", m.line);
    }

    if (matches.length == 0)
        return;

    writeln("Type the number of topic to open it, or type 'skip' to return");

    string response = strip(readln());

    if (response == "skip")
        return;

    try
    {
        int index = to!int(response);

        if (index < 0 || index >= matches.length)
        {
            writeln("Invalid selection.");
            return;
        }

        string content = readText(matches[index].path);
        writeln(YELLOW,"---- FILE CONTENT (", matches[index].path, ") ----"<RESET);
        writeln(content);
    }
    catch (Exception)
    {
        writeln("Invalid input.");
    }
}

void searchContent(TopicName[] topics, string topic)
{
    string input = strip(topic);
    writeln(BLUE,"Searching files for ",topic,RESET);

    for (int i = 0; i < 81; i++)
    {
        write(BLUE,"#",RESET);
        Thread.sleep( 10.dur!("msecs") );
    }
    writeln("");

    foreach (t; topics)
    {
        if (t.topicName == input)
        {
            try
            {
                string content = readText(t.topicPath);
                write("\x1b[1A");  // Cursor up 1
                write("\x1b[2K");  // Clear entire line
                write("\x1b[1A");
                write("\x1b[2K");
                // Return cursor to the start of the line
                write("\r");

                writeln(YELLOW,"---- FILE CONTENT (", t.topicPath, ") ----",RESET);
                writeln(content);
            }
            catch (Exception)
            {
                writeln("Error while reading the file");
            }
            return;
        }
    }

    TopicName[] relativeMatches;

    foreach (key; topics)
    {
        if (key.topicName.toLower().canFind(input.toLower()))
        {
            relativeMatches ~= key;
        }
    }

    if (relativeMatches.length == 0)
    {
        writeln(RED,"No topics found containing '",input,"'",RESET);
        return;
    }

    writeln(YELLOW,"No exact matches were found! Relative matches: ",RESET);
    
    foreach (i, t; relativeMatches)
    {
        writeln("[",i,"]",t.topicName," : ",t.topicPath);
    }

    writeln("Type the number of the topic to open it, or 'skip' to return");
    string response = strip(readln());

    if (response == "skip") return;

    try
    {
        int index = to!int(response);
        if (index < 0 || index >= relativeMatches.length)
        {
            writeln(RED,"Invalid selection",RESET);
            return;
        }

        string content = readText(relativeMatches[index].topicPath);
        writeln(YELLOW,"---- FILE CONTENT (", relativeMatches[index].topicPath, ") ----",RESET);
        writeln(content);
    }
    catch (Exception)
    {
        writeln(RED,"Invalid input",RESET);
    }
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
        if (version_type == "windows") {spawnShell("cls").wait; 
        drawBar("DREAMSTUDIO TERMINAL-BASED MANUAL"); drawCustomPanel();
        writeWelcome();}
        if (version_type == "linux" || version_type == "macos")
            {spawnShell("clear").wait; 
            drawBar("DREAMSTUDIO TERMINAL-BASED MANUAL");drawCustomPanel();
            writeWelcome();}
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

        else if (toLower(command_identifier) == "search" &&
        toLower(command_type == "several"))
        {
            searchSeveral("./docs", search_param);
        }

        else if (toLower(command_identifier) == "open" &&
        toLower(command_type) == "pdf")
        {
            openPDF("./docs/manual.pdf");
        }
        else
        {
            searchContent(topicsNames, arg);
        }
    }
}

void main()
{
    version(Windows)
        {
            try
            {
                spawnShell("cls").wait;
            } catch (ProcessException e)
            {
                writeln("Error Occured: ",e);
            }
        }
    else
    {
        try
        {
            spawnShell("clear").wait;
        } catch (ProcessException e)
        {
            writeln("Error Occurred: ",e);
        }
    }

    drawBar("COPYRIGHT 2026 DREAMSTUDIO TERMINAL-BASED MANUAL - ALL RIGHTS RESERVED");
    drawCustomPanel();
    writeWelcome();
    while(true)
    {
        write("> ");
        string user_input = readln();
        writeln("");
        parseUserInput(user_input);
    }
}
