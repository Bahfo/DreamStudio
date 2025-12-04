from prompt_toolkit import prompt
from prompt_toolkit.styles import Style
from rich.console import Console

welcome_message = """COPYRIGHT 2026 EX-TECHNOLOGIES \nNINJASPY Processes Manager"""

class manager(Console):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.print(f"[bold #ADADAD]{welcome_message}[/bold #ADADAD]")

if __name__ == '__main__':
    console = manager()