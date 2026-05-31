import pickle
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer()
console = Console()


@app.command()
def hello():
    console.print("Is my mic on????")


if __name__ == "__main__":
    app()
