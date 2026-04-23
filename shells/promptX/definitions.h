#include <stdbool.h>
#include <unistd.h>
#include <string.h>
#include <stdio.h>

#define BLACK   "\033[0;30m"
#define RED     "\033[0;31m"
#define GREEN   "\033[0;32m"
#define YELLOW  "\033[0;33m"
#define BLUE    "\033[0;34m"
#define MAGENTA "\033[0;35m"
#define CYAN    "\033[0;36m"
#define WHITE   "\033[0;37m"

#define RESET        "\033[0m"
#define BOLD         "\033[1m"
#define DIM          "\033[2m"
#define ITALIC       "\033[3m"
#define UNDERLINE    "\033[4m"
#define BLINK        "\033[5m"
#define REVERSE      "\033[7m"
#define HIDDEN       "\033[8m"
#define STRIKETHROUGH "\033[9m"

// prints the welcome message on the screen
void _print_welcome();