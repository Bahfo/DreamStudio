/*
The Text-User-Interface for the search engine.
SYNTAX: 
    Shell-Search <Command> <args>
                 <Command> <Command Name>
                 <Args>    <Arguments>
*/

#include <time.h>
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <searchFile.h>

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