grammar Lavender;

// LEXER RULES

// Keywords
IF       : 'if';
ELIF     : 'elif' | 'else if';
ELSE     : 'else';
DO       : 'do';
WHILE    : 'while';
PRINT    : 'print' | 'write';
INPUT    : 'read' | 'input';
VARIABLE : 'var' | 'let';
FUNCTION : 'function' | 'define';
METHOD   : 'new' | 'method';
MACRO    : 'macro';
CLASS    : 'class';
NAMESPC  : 'namespace';
BOOL     : 'true' | 'false';

// Literals
UINT     : [0-9]+ ;
SINT     : [+-]?[0-9]+ ;
UFLOAT   : [0-9]+ ('.' [0-9]+)? ([eE][+-]?[0-9]+)? ;
SFLOAT   : [+-]?[0-9]+ ('.' [0-9]+)? ([eE][+-]?[0-9]+)? ;
STRING   : '"' (~["\r\n])* '"' ;
CHAR     : '\'' (~['\r\n])* '\'' ;
UBINARY  : '0b'[01]+ ;
SBINARY  : '1b'[01]+ ;
UHEX     : '0x'[0-9A-Fa-f]+ ;
SHEX     : '1x'[0-9A-Fa-f]+ ;

// Operators and Symbols
PLUS      : '+' ;
MINUS     : '-' ;
MULT      : '*' ;
DIVD      : '/' ;
POWER     : '^' ;
MODULUS   : '%' ;
EQUAL     : '==' ;
NOTEQ     : '!==' ;
ASSIGN    : '=' ;
LESS      : '<' ;
BIGGER    : '>' ;
LESSEQ    : '<=' ;
BIGGEREQ  : '>=' ;
LPAREN    : '(' ;
RPAREN    : ')' ;
LBRACE    : '{' ;
RBRACE    : '}' ;
SEMI      : ';' ;
COMMA     : ',' ;

// Identifiers
IDENTIFY  : [a-zA-Z_][a-zA-Z0-9]* ;

// Whitespace & Comments
WS        : [ \t\r\n]+ -> skip ;
COMMENT   : '#' ~[\r\n]* -> skip ;
MULTICOM  : '###' .*? '###' -> skip ;


// PARSER RULES

program
    : statement+ EOF
    ;

statement
    : declareVar
    | assignment
    | condition
    | loop
    | commandStatement
    ;

// Expressions (with funcCall)
expr
    : funcCall
    | UINT
    | SINT
    | UFLOAT
    | SFLOAT
    | STRING
    | CHAR
    | BOOL
    | UBINARY
    | SBINARY
    | UHEX
    | SHEX
    | IDENTIFY
    | '(' expr ')'
    | '{' expr '}'
    | expr op=('*'|'/') expr
    | expr op=('+'|'-') expr
    | expr op=('==' | '!==') expr
    | expr op=('>' | '<' | '>=' | '<=') expr
    ;

// Variable Declaration & Assignment
declareVar
    : VARIABLE IDENTIFY (ASSIGN expr)? SEMI
    ;

assignment
    : IDENTIFY ASSIGN expr SEMI
    ;

// Function Call
funcCall
    : IDENTIFY LPAREN (expr (COMMA expr)*)? RPAREN
    ;

// Conditions
condition
    : IF LPAREN expr RPAREN LBRACE statement+ RBRACE
      (ELIF LPAREN expr RPAREN LBRACE statement+ RBRACE)*
      (ELSE LBRACE statement+ RBRACE)?
    ;

// Loops
loop
    : WHILE LPAREN expr RPAREN LBRACE statement+ RBRACE
    | DO LBRACE statement+ RBRACE WHILE LPAREN expr RPAREN
    ;

// Commands
commandStatement
    : PRINT LPAREN (STRING | CHAR | IDENTIFY | expr)* RPAREN SEMI
    | FUNCTION IDENTIFY LPAREN (IDENTIFY (COMMA IDENTIFY)*)? RPAREN LBRACE statement+ RBRACE
    ;
