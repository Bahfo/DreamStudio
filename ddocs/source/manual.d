module ddocs.manual;
import std.stdio, std.process, std.string, std.exception, std.file, std.path, std.uni;
import core.stdc.stdlib;

string available_commands = q{ALL AVAILABLE COMMANDS:
GENERAL      : clear, exit, help
GET FAMILY   : get-started, get-commands
SEARCH FAMILY: search-topic, search-several
OPEN FAMILY  : open-pdf, open-web};

string checkVersion()
{
    version(Windows) return "windows";
    version(linux)   return "linux";
    version(OSX)     return "macos";
}

void writeWelcome()
{
    writeln("┌────────────────────────────────────────────────────────────────────────────────┐");
    writeln("│            Welcome to DreamStudio's Terminal Documentation DDocs               │");
    writeln("│            Please enter the name of the topic you are looking for              │");
    writeln("│            For starting up, read 'welcome' by typing 'get-started'             │");
    writeln("└────────────────────────────────────────────────────────────────────────────────┘");
    writeln(" THIS TOOL WAS DEVELOPED USING THE D-PROGRAMMING LANGUAGE. FREE AND FAST C-STYLE. ");
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
        string help_content = cast(string) readText("help.dsman");
        writeln(help_content);
    }

    else
    {
        if (toLower(command_identifier) == "get" &&
        toLower(command_type) == "started")
        {
            string contents = cast(string) readText("get_started.dsman");
            writeln(contents);
        }

        else if(toLower(command_identifier) == "get" &&
        toLower(command_type) == "commands")
        {
            writeln(available_commands);
        }

        else if (toLower(command_identifier) == "search")
        {

        }

        else if (toLower(command_identifier) == "open")
        {

        }
        else
        {
            writeln("Unknown command: Please type-in the correct command");
            writeln("or type 'get-commands' to see full commands list");
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
        parseUserInput(user_input);
    }
}
