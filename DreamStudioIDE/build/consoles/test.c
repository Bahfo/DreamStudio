#include <stdio.h>

int main(){
    volatile asm {
        "mov ax,25"
        "mov bx,30"
        "mul bx"
    };
}