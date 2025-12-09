from prompt_toolkit import prompt
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel

console = Console()

pt_style = Style.from_dict(
    {
        "prompt": "bold #00ff00",
    }
)


def main():
    console.print(
        Panel(
            "[bold cyan]Welcome to the Rich + Prompt-Toolkit Demo[/bold cyan]",
            expand=False,
        )
    )

    while True:
        user_input = prompt(
            [("class:prompt", "Enter a command (or 'exit'): ")], style=pt_style
        )

        if user_input.strip().lower() == "exit":
            console.print("\n[bold red]Exiting...[/bold red]")
            break

        console.print(
            f"[bold green]You typed:[/bold green] [yellow]{user_input}[/yellow]"
        )

        console.print(
            Panel(
                f"[magenta]Length of input:[/magenta] {len(user_input)}", expand=False
            )
        )


if __name__ == "__main__":
    main()
