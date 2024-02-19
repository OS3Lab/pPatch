import os
import re
import subprocess

import typer
import whatthepatch

from ppatch.model import File, Line
from ppatch.utils.resolve import apply_change

app = typer.Typer()

BASE_DIR = "/home/jingfelix/workspace/repos/pPatch"
PATCH_STORE_DIR = "_patches"


@app.command()
def show(filename: str):
    """
    Show detail of a patch file."""
    if not os.path.exists(filename):
        typer.echo(f"Warning: {filename} not found!")
        return

    content = ""
    with open(filename, mode="r", encoding="utf-8") as (f):
        content = f.read()

    diffes = whatthepatch.parse_patch(content)

    for diff in diffes:
        typer.echo(f"diff: {diff.header}")


@app.command()
def trace(filename: str, from_commit: str = "", to_commit: str = "HEAD"):
    if not os.path.exists(filename):
        typer.echo(f"Warning: {filename} not found!")
        return

    typer.echo(f"tracing patch {filename} from {from_commit} to {to_commit}")

    output: str = subprocess.run(
        [
            "git",
            "log",
            "--pretty=format:%H",
            "--",
            filename,
        ],
        capture_output=True,
    ).stdout.decode("utf-8")

    sha_list = output.splitlines()

    # 在 sha_list 中找到 from_commit 和 to_commit 的位置
    from_index = sha_list.index(from_commit) if from_commit else -1
    if from_index == -1:
        typer.echo(f"from_commit {from_commit} not found")
        return

    # 注意此处需要多选一个，包含 from commit 前面的一个 commit，用于 checkout
    sha_list = sha_list[: from_index + 2]

    typer.echo(f"Get {len(sha_list)} commits for {filename}")

    # checkout 到 from_commit 前面的一个 commit
    subprocess.run(
        ["git", "checkout", sha_list.pop(), "--", filename], capture_output=True
    )

    origin_file = File(file_path=filename)
    # 首先将最后一个 patch 以 flag=True 的方式 apply
    patch_path = os.path.join(BASE_DIR, PATCH_STORE_DIR, f"{sha_list.pop()}.patch")
    for diff in whatthepatch.parse_patch(patch_path):
        if diff.header.old_path == filename or diff.header.new_path == filename:
            new_line_list, _ = apply_change(
                diff.changes, origin_file.line_list, flag=True
            )
            break

    confict_list: list[list[Line]] = []

    # 注意这里需要反向
    for sha in sha_list.reverse():
        patch_path = os.path.join(BASE_DIR, PATCH_STORE_DIR, f"{sha}.patch")

        with open(patch_path, mode="r", encoding="utf-8") as (f):
            diffes = whatthepatch.parse_patch(f.read())

            for diff in diffes:
                if diff.header.old_path == filename or diff.header.new_path == filename:
                    new_line_list, flag_line_list = apply_change(
                        diff.changes, new_line_list, flag=True
                    )
                    break

        assert isinstance(flag_line_list, list)

        if len(flag_line_list) > 0:
            confict_list.append(flag_line_list)
            typer.echo(f"Conflict found in {sha}")
            for line in flag_line_list:
                typer.echo(f"{line.index + 1}: {line.content}")

    typer.echo(f"Conflict count: {len(confict_list)}")
    typer.echo(f"Conflict list: {confict_list}")


@app.command()
def getpatches(filename: str, expression: str = None):
    """
    Get patches of a file.
    """
    if not os.path.exists(filename):
        typer.echo(f"Warning: {filename} not found!")
        return

    typer.echo(f"Get patches of {filename}")

    output: str = subprocess.run(
        ["git", "log", "-p", "--", filename], capture_output=True
    ).stdout.decode("utf-8")

    # 将 output 按照 commit ${hash}开头的行分割
    patches: list[str] = []
    for line in output.splitlines():
        if line.startswith("commit "):
            patches.append(line + "\n")
        else:
            patches[-1] += line + "\n"

    typer.echo(f"Get {len(patches)} patches for {filename}")

    pattern = re.compile(expression) if expression is not None else None

    for patch in patches:
        sha = patch.splitlines()[0].split(" ")[1]

        if pattern is not None and pattern.search(patch) is None:
            typer.echo(f"Patch {sha} found with expression {expression}")

        patch_path = os.path.join(BASE_DIR, PATCH_STORE_DIR, f"{sha}.patch")

        if not os.path.exists(patch_path):
            with open(patch_path, mode="w+", encoding="utf-8") as (f):
                f.write(patch)


# diff(
#     header=header(
#         index_path=None,
#         old_path="kernel/cgroup/cgroup-v1.c",
#         old_version="ee93b6e895874",
#         new_path="kernel/cgroup/cgroup-v1.c",
#         new_version="527917c0b30be",
#     ),
#     changes=[
#         Change(
#             old=912,
#             new=912,
#             line="\topt = fs_parse(fc, cgroup1_fs_parameters, param, &result);",
#             hunk=1,
#         ),
#         Change(old=913, new=913, line="\tif (opt == -ENOPARAM) {", hunk=1),
#         Change(
#             old=914,
#             new=914,
#             line='\t\tif (strcmp(param->key, "source") == 0) {',
#             hunk=1,
#         ),
#         Change(
#             old=None,
#             new=915,
#             line="\t\t\tif (param->type != fs_value_is_string)",
#             hunk=1,
#         ),
#         Change(
#             old=None,
#             new=916,
#             line='\t\t\t\treturn invalf(fc, "Non-string source");',
#             hunk=1,
#         ),
#         Change(old=915, new=917, line="\t\t\tif (fc->source)", hunk=1),
#         Change(
#             old=916,
#             new=918,
#             line='\t\t\t\treturn invalf(fc, "Multiple sources not supported");',
#             hunk=1,
#         ),
#         Change(old=917, new=919, line="\t\t\tfc->source = param->string;", hunk=1),
#     ],
#     text='diff --git a/kernel/cgroup/cgroup-v1.c b/kernel/cgroup/cgroup-v1.c\nindex ee93b6e895874..527917c0b30be 100644\n--- a/kernel/cgroup/cgroup-v1.c\n+++ b/kernel/cgroup/cgroup-v1.c\n@@ -912,6 +912,8 @@ int cgroup1_parse_param(struct fs_context *fc, struct fs_parameter *param)\n \topt = fs_parse(fc, cgroup1_fs_parameters, param, &result);\n \tif (opt == -ENOPARAM) {\n \t\tif (strcmp(param->key, "source") == 0) {\n+\t\t\tif (param->type != fs_value_is_string)\n+\t\t\t\treturn invalf(fc, "Non-string source");\n \t\t\tif (fc->source)\n \t\t\t\treturn invalf(fc, "Multiple sources not supported");\n \t\t\tfc->source = param->string;\n-- \ncgit \n\n',
# )
