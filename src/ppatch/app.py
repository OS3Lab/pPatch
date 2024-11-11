import logging
import os

import typer
from rich.console import Console
from rich.logging import RichHandler

logging.basicConfig(level=logging.INFO, handlers=[RichHandler()], format="%(message)s")
logger = logging.getLogger()

from ppatch.config import settings
from ppatch.utils.common import post_executed

app = typer.Typer(result_callback=post_executed, no_args_is_help=True)


@app.callback(invoke_without_command=True)
def callback(verbose: bool = False, version: bool = False):
    """
    Entry for public options
    """
    if verbose:
        logger.setLevel(logging.DEBUG)

    if version:

        from ppatch.__version__ import __version__

        console = Console()
        console.print(f"ppatch version {__version__}")
        raise typer.Exit()

    # Check Current path
    current_path = os.path.abspath(os.getcwd())

    logger.debug(f"Current path: {current_path}")
    logger.debug(f"Work directory: {settings.work_dir}")

    if current_path != settings.work_dir:
        logger.warning(
            f"Current path ({current_path}) is not the same as the configured work directory ({settings.work_dir})."
        )


from ppatch.commands.apply import apply
from ppatch.commands.auto import auto
from ppatch.commands.cache import clear_cache
from ppatch.commands.get import getpatches
from ppatch.commands.help import show_settings
from ppatch.commands.show import show
from ppatch.commands.symbol import getsymbol_command
from ppatch.commands.trace import trace_command
