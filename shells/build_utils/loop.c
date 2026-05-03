#include "definitions.h"

int main()
{
    char buffer[8192];
    while (true)
    {
        printf("PROMPTX>>> ");
        if (!fgets(buffer, sizeof(buffer), stdin)) 
            break;
        else buffer[strcspn(buffer, "\n")] = '\0';

        if (strcmp(buffer, "exit") == 0) break;
        if (strcmp(buffer, "help") == 0) _print_welcome();
        char *result = buffer;
        printf(result);
    }
    return 0;
}