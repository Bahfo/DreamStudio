import customtkinter as ctk
import pyperclip

def b_sharp_terminal_on_call():
    B_SHARP_terminal_window = ctk.CTk()
    B_SHARP_terminal_window.title("B# Terminal")
    B_SHARP_terminal_window.iconbitmap(r"icons\b_sharp.ico")
    B_SHARP_terminal_window.minsize(900,500)
    B_SHARP_terminal_window.configure(bg="#1e1e1e")

    terminal_text_editor = ctk.CTkTextbox(B_SHARP_terminal_window,font=("Consolas",16))
    terminal_text_editor.configure(spacing1=4, spacing3=4, spacing2=2)
    terminal_text_editor.pack(side="left",fill="both",padx=(5,5),pady=(5,5),expand=True)

    def on_enter_key_hit(event=None):
        terminal_text = terminal_text_editor.get("current linestart","current lineend")
        pyperclip.copy(terminal_text)

    terminal_text_editor.bind('<Return>',on_enter_key_hit)

    def terminal_text_Lexer(text):
        
        TT_INT = 'INT'
        TT_FLOAT = 'FLOAT'
        TT_MINUS = 'MINUS'
        TT_PLUS = 'PLUS'
        TT_MULTIPLY = 'MULTIPLY'
        TT_DIVIDE = 'DIVIDE'
        TT_LPARENT = 'L-PARENTHISIS'
        TT_RPARENT = 'R-PARENTHISIS'

        class Tokens:
            def __init__(self,_type,value=None):
                self._type = _type
                self.value = value

            def __repr__(self):
                if self.value:
                    return f'{self._type}:{self.value}'
                return f'{self._type}'
            
        class Lexer:
            def __init__(self, text):
                self.text         = text
                self.position     = -1
                self.current_char = None
                self.__advance__()

            def __advance__(self):
                self.position += 1
                if self.position < len(self.text):
                    self.current_char = self.text[self.position]
                else:
                    self.current_char = None

            def __tokens_generator__(self):
                tokens = []

                while self.current_char != None:
                    if (self.current_char == ' ' or self.current_char == '\t'): 
                        self.__advance__()
                    elif self.current_char == '+':
                        tokens.append(Tokens(TT_PLUS,'+'))
                    elif self.current_char == '-':
                        tokens.append(Tokens(TT_MINUS,'-'))
                    elif self.current_char == '*':
                        tokens.append(Tokens(TT_MULTIPLY,'*'))
                    elif self.current_char == '/':
                        tokens.append(Tokens(TT_DIVIDE,'/'))
                    elif self.current_char == '(':
                        tokens.append(Tokens(TT_LPARENT,'('))
                    elif self.current_char == ')':
                        tokens.append(Tokens(TT_RPARENT,')'))

                    return tokens

                def __numbers_identifier__():
                    number_of_points = 0
                    string_of_numbers = []
                    list_of_numbers = '0123456789'
                    while self.current_char in list_of_numbers or (self.current_char == '.' and number_of_points == 0):
                        if self.current_char == '.':
                            points += 1
                        string_of_numbers.append(self.current_char)
                        self.__advance__()
                    
                    if number_of_points == 1:
                        tokens.append(Tokens(TT_FLOAT,float(''.join(string_of_numbers))))
                    else:
                        tokens.append(Tokens(TT_INT,int(''.join(string_of_numbers))))

                lexer  = Lexer(text)
                tokens = lexer.__tokens_generator__()
                terminal_text_editor.insert("3.0",tokens)

    terminal_text_Lexer(pyperclip.paste())

    B_SHARP_terminal_window.mainloop()

b_sharp_terminal_on_call()