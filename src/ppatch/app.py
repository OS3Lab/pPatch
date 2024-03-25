import typer

app = typer.Typer()

BASE_DIR = "/home/laboratory/workspace/exps/ppatch"
PATCH_STORE_DIR = "_patches"


from ppatch.commands.auto import auto
from ppatch.commands.get import getpatches
from ppatch.commands.show import show
from ppatch.commands.trace import trace
