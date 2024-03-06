import subprocess

# import typer
# import whatthepatch

# from ppatch.model import Line
# from .resolve import apply_change


def clean_repo():
    subprocess.run(["git", "clean", "-df"])
    subprocess.run(["git", "reset", "--hard"])


# def _apply(
#     patch_path: str,
#     filename: str,
#     new_line_list: list[Line],
#     from_commit_sha: str,
#     flag: bool = False,
# ) -> tuple[list[Line], list[Line]]:
#     for diff in whatthepatch.parse_patch(
#         open(patch_path, mode="r", encoding="utf-8").read()
#     ):
#         if diff.header.old_path == filename or diff.header.new_path == filename:
#             try:
#                 new_line_list, flag_line_list = apply_change(
#                     diff.changes, new_line_list, flag=flag
#                 )
#             except Exception as e:
#                 typer.echo(f"Apply patch {from_commit_sha} failed")
#                 typer.echo(f"Error: {e}")
#                 return [], []

#             return new_line_list, flag_line_list

#         else:
#             typer.echo(f"Do not match with {filename}, skip")


def process_title(filename: str):
    """
    Process the file name to make it suitable for path
    """
    return "".join([letter for letter in filename if letter.isalnum()])


def find_list_positions(main_list: list, sublist: list) -> list[int]:
    sublist_length = len(sublist)
    positions = []

    for i in range(len(main_list) - sublist_length + 1):
        if main_list[i : i + sublist_length] == sublist:
            positions.append(i)

    return positions
