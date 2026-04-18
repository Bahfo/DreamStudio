logo_ascii = r"""

        ░▒▓███████▓▒░▒▓███████▓▒░  ░▒▓██████▓▒░░▒▓███████▓▒░░▒▓████████▓▒░▒▓█▓▒░        
        ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░        
        ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░        
        ░▒▓██████▓▒░░▒▓███████▓▒░ ░▒▓████████▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓██████▓▒░ ░▒▓█▓▒░        
              ░▒▓█▓▒░▒▓█▓▒░       ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░        
              ░▒▓█▓▒░▒▓█▓▒░       ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░        
       ░▒▓███████▓▒░░▒▓█▓▒░       ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓████████▓▒░▒▓████████▓▒░ 

────────────────────────────────────────────────────────────────────────────────────────────────
                                 SPANEL INTERACTIVE SHELL                 
                                    © EX Technologies
────────────────────────────────────────────────────────────────────────────────────────────────

────────────────────────────────────────────────────────────────────────────────────────────────
COMMAND INDEX:
• Display help documentation:              help

────────────────────────────────────────────────────────────────────────────────────────────────
NOTE:
All command inputs are processed sequentially by the terminal's
core interpreter. Invalid or malformed syntax may result in
undefined behavior or ignored operations.
────────────────────────────────────────────────────────────────────────────────────────────────

Below is a detailed list of available documented commands:

clear           Clears terminal screen
clearhistory    Clears the commands history (with errors commands)
help            Documentation Help of a specific command or topic
────────────────────────────────────────────────────────────────────────────────────────────────
                                    END OF DOCUMENTATION
────────────────────────────────────────────────────────────────────────────────────────────────
"""


from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console

from spanel.connection import ConnectionManager, ConnectionSession, CommandLine


class SPanel:
    """
    Terminal UI layer using:
    - prompt_toolkit (input handling)
    - rich (output rendering)

    Delegates execution to CommandLine.
    """

    def __init__(self, command_line):
        self.command_line = command_line

        self.console = Console()
        self.history = InMemoryHistory()
        self.session = PromptSession(history=self.history)

    def run(self):
        while True:
            try:
                user_input = self.session.prompt(">>> ")

                result = self.command_line.execute(user_input)

                self.render(result)

            except KeyboardInterrupt:
                continue

            except EOFError:
                break

    def render(self, result):
        if not result:
            return

        # CLEAR COMMAND
        if isinstance(result, dict) and result.get("type") == "clear":
            self.console.clear()
            return

        # SSH OUTPUT
        if isinstance(result, dict) and "stdout" in result:
            if result["stdout"]:
                self.console.print(result["stdout"])

            if result.get("stderr"):
                self.console.print(result["stderr"], style="red")

            return

        # ERROR TYPE
        if isinstance(result, dict) and result.get("type") == "error":
            self.console.print(result.get("data", ""), style="red")
            return

        # GENERIC STRING OUTPUT
        if isinstance(result, str):
            self.console.print(result)
            return


if __name__ == "__main__":
    app = SPanel(CommandLine(None))
    app.run()
