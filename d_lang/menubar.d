module menubar;

import std.conv;
import std.stdio;
import std.string;
import std.process;

version(Windows)
{
    import core.sys.windows.windows;
}

ulong getTerminalWidth()
{
    version (Windows)
    {
        CONSOLE_SCREEN_BUFFER_INFO csbi;
        auto handle = GetStdHandle(STD_OUTPUT_HANDLE);

        if (GetConsoleScreenBufferInfo(handle, &csbi))
            return csbi.srWindow.Right - csbi.srWindow.Left + 1;

        return 80;
    }
    else version (Posix)
    {
        import core.sys.posix.sys.ioctl;
        import core.sys.posix.unistd;

        winsize ws;

        if (ioctl(STDOUT_FILENO, TIOCGWINSZ, &ws) == 0)
            return ws.ws_col;

        return 80;
    }
    else
    {
        return 80;
    }
}

void moveCursor(int row, int col)
{
    version (Windows)
    {
        HANDLE hOut = GetStdHandle(STD_OUTPUT_HANDLE);
        COORD pos;
        pos.X = cast(short)(col - 1);
        pos.Y = cast(short)(row - 1);
        SetConsoleCursorPosition(hOut, pos);
    }
    else version (Posix)
    {
        writef("\x1b[%d;%dH", row, col);
    }
}

void drawBar(string text_to_show)
{
    auto width = getTerminalWidth();

    write("\x1b[H");
    write("\x1b[7m");

    foreach (i; 0 .. width)
        write(" ");

    write("\r");

    int padding = (cast(int)width - cast(int)text_to_show.length) / 2;

    writef("%*s%s", padding, "", text_to_show);

    writeln("\x1b[0m");
}

void drawCustomPanel()
{
    int width = cast(int)getTerminalWidth();

    moveCursor(2, width - 40);
    foreach(i; 0 .. 20)
        write(" ");

    moveCursor(2, width - 40);
    writeln("┌──────────────────┬───────────────────┐");

    moveCursor(3, width - 40);
    writeln("│ UTILITY MANAGER  │ STUDIO'S VERSION  │");

    moveCursor(4, width - 40);
    writeln("│ - help           │ VERSION 1.0.0     │");

    moveCursor(5, width - 40);
    writeln("│ - list           │                   │");

    moveCursor(6, width - 40);
    writeln("│ - install <tool> │                   │");

    moveCursor(7, width - 40);
    writeln("└──────────────────┴───────────────────┘");

    moveCursor(2,1);
}
