import os

import typer
from rich import print as rprint
from rich.prompt import Confirm

from ppatch.app import app
from ppatch.config import settings


def clear_patch_cache():
    # patch_store_dir 和 base_dir 在 config 中定义
    patch_store_path = os.path.join(settings.base_dir, settings.patch_store_dir)

    if os.path.exists(patch_store_path) and os.path.isdir(patch_store_path):
        for item in os.listdir(patch_store_path):
            if os.path.isfile(item):
                os.remove(item)
        typer.echo("Cache cleared.")
    else:
        typer.echo(f"Cache directory {patch_store_path} does not exist.")


@app.command(name="clear-cache")
def clear_cache():
    """Clear patch cache"""
    rprint("[bold red]Warning: This operation will delete all patch caches![/bold red]")
    if Confirm.ask("Are you sure you want to continue?"):
        pass
        # clear_patch_cache()
    else:
        rprint("[blue]Operation cancelled.[/blue]")
