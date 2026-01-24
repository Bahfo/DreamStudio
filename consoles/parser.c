/*
COMMAND LINE INTERFACE FOR PROGRAMMERS (WILDCAT)
Better Usage Utility for Programmers Written in C

WHAT DOES THIS TOOL HAVE?
1. Search Patterns in Files
2. File Information
3. File Documentation Grapper
4. Managing Files

WHAT LIBRARIES AND MODULES NEEDED?
1. Regular Expressions
2. A Way to communicate with the operating system
3. String Modules
4. CLI tool builder
*/

#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <time.h>

#define  BUFFER_SIZE 512
char inputStream[BUFFER_SIZE];
time_t currentTime;

void userCommandParser(char *userInput){
    char *token = strtok(userInput," ");

    if (strcmp(token, "hello")==0){
        printf("Hello World!\n");
    }
    else if (strcmp(token, "time")==0){
        time(&currentTime);
        printf("Current Time: %s",ctime(&currentTime));
    }
}

int main() {
    while (true){
        if (fgets(inputStream, sizeof(inputStream), stdin) == NULL){
            break;
        }

        inputStream[strcspn(inputStream,"\n")] = '\0';
        if (strcmp(inputStream,"exit")==0){
            break;
        }
        else{
            userCommandParser(inputStream);
        }
    }
    return 0;
}