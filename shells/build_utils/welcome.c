#include "definitions.h"

void _print_welcome()
{
    char *name = 
        "$$$$$$$\\                                               $$\\     $$\\   $$\\\n"
        "$$  __$$\\                                              $$ |    $$ |  $$ |\n"
        "$$ |  $$ | $$$$$$\\   $$$$$$\\  $$$$$$\\$$$$\\   $$$$$$\\ $$$$$$\\   \\$$\\ $$  |\n"
        "$$$$$$$  |$$  __$$\\ $$  __$$\\ $$  _$$  _$$\\ $$  __$$\\\\_$$  _|   \\$$$$  /\n"
        "$$  ____/ $$ |  \\__|$$ /  $$ |$$ / $$ / $$ |$$ /  $$ | $$ |     $$  $$< \n"
        "$$ |      $$ |      $$ |  $$ |$$ | $$ | $$ |$$ |  $$ | $$ |$$\\ $$  /\\$$\\\n"
        "$$ |      $$ |      \\$$$$$$  |$$ | $$ | $$ |$$$$$$$  | \\$$$$  |$$ /  $$ |\n"
        "\\__|      \\__|       \\______/ \\__| \\__| \\__|$$  ____/   \\____/ \\__|  \\__|\n"
        "                                            $$ |\n"
        "                                            $$ |\n"
        "                                            \\__|\n";

    char *descriptor_help_table = 
        "PromptX is a powerful advanced REPL shell developed for automation and extreme customizability.\n"
        "┌─────────────────────────────────┬─────────────────────────────────┬──────────────────────────┐\n"
        "│     EXCELLENT TECHNOLOGIES      │        DREAMSTUDIO TEAM         │     PROMPTX-PROJECT      │\n"
        "└─────────────────────────────────┴─────────────────────────────────┴──────────────────────────┘\n";

    printf(RED "%s" RESET, name);
    printf(YELLOW "(C) Copyright - All rights reserved\n" RESET);
    printf("Welcome to PromptX Shell!\n");
    printf("Developed By DreamStudio Team - Excellent Technologies\n");
    printf("\n");
    printf(descriptor_help_table);
}