from prompt_toolkit import PromptSession
from prompt_toolkit.lexers import Lexer
import prompt_toolkit.styles as pts
from rich.console import Console
from rich.style import Style
from rich.panel import Panel
from rich.theme import Theme
from rich.text import Text
import shlex


help = """Help: help  //Shows documentation

"""


welcome_message = """COPYRIGHT 2026 EX-TECHNOLOGIES \nDreamStudio Download Manager"""
EXPLAIN1 = """Unlock next capabilities, communicate and get extensions via """
URL = r"""https:\\example.com"""

theme = Theme({"cmd.keyword":"yellow"})
WARNING_STYLE = Style(color="red",bold=True)
WELCOME_STYLE = Style(color="#0056A6")

COMMANDS = ['clear','update','ensure','exit','fetch','help','show']
FLAGS = {
    "--source":"value",
    "--destination":"value",
    "-src":"value",
    "-dest":"value",
    "--force":"flag",
    "-f":"flag",
    "--help":"flag",
    "-h":"flag",
    "--version":"flag",
    "-v":"flag",
}

class ManagerLexer(Lexer):
    def lex_document(self, document):
        text = document.text

        def get_line_tokens(line_number):
            line = document.lines[line_number]
            tokens = []

            words = line.split(' ')
            for word in words:
                if word in COMMANDS:
                    tokens.append(('class:yellow', word + ' '))
                elif word in FLAGS.keys():
                    tokens.append(('class:green', word + ' '))
                else:
                    tokens.append(('', word + ' '))
            return tokens

        return get_line_tokens

style= pts.Style.from_dict({'yellow':'yellow','green':"#5E5E5E"})
session = PromptSession(lexer=ManagerLexer(),style=style)

class manager(Console):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        panel = Panel(Text(welcome_message,justify="center"),style=WELCOME_STYLE)
        self.print(panel)
        self.print(f"{EXPLAIN1}[#575757 link=https://example.com]{URL}[/#575757 link]")

        #################################################################################
        # COMMANDS LOOP
        #################################################################################
        while True:
            try:
                command = session.prompt(f"Download Manager >>> ")
                arg = self.parse_command(command)

                if arg:
                    self.print(arg)

            except (EOFError, KeyboardInterrupt):
                break

    def parse_command(self, input):
        tokens = shlex.split(input)
        
        if not tokens:
            return
        
        command = tokens[0]
        args = tokens[1:]

        def parse_args(args, option_keys):
            parsed = {}
            skip_next = False
            for i, token in enumerate(args):
                if skip_next:
                    skip_next = False
                    continue

                if token in option_keys:
                    if option_keys[token] == "value":
                        if i + 1 < len(args):
                            parsed[token] = args[i + 1]
                            skip_next = True
                        else:
                            parsed[token] = None
                    
                    elif option_keys[token] == "flag":
                        parsed[token] = True

                else:
                    if "positional" not in parsed:
                        parsed["positional"] = []
                    parsed["positional"].append(token)
            return parsed
        arguments_parsed = parse_args(args=args, option_keys=FLAGS)

        def execute(command, parsed_args):
            if command == "help":
                if parsed_args == '--help' or parsed_args == '-h':
                    print("Help Command: Download Manager")
            else:
                print(f"Unkown Command: {command}")
        execute(command=command, parsed_args=arguments_parsed)

if __name__ == "__main__":
    console = manager()
