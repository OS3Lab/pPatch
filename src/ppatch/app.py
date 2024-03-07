import os
import re
import subprocess

import typer
import whatthepatch

from ppatch.model import File, Line
from ppatch.utils.common import process_title
from ppatch.utils.resolve import apply_change

app = typer.Typer()

BASE_DIR = "/home/laboratory/workspace/exps/ppatch"
PATCH_STORE_DIR = "_patches"


@app.command()
def show(filename: str):
    """
    Show detail of a patch file.
    """
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
def trace(filename: str, from_commit: str = ""):
    if not os.path.exists(filename):
        typer.echo(f"Warning: {filename} not found!")
        return

    typer.echo(f"tracing patch {filename} from {from_commit}")

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

    # 注意此处需要多选一个，包含 from commit 的前一个，用于 checkout
    sha_list = sha_list[: from_index + 2]

    typer.echo(f"Get {len(sha_list)} commits for {filename}")

    # checkout 到 from_commit 的前一个 commit
    subprocess.run(
        ["git", "checkout", sha_list.pop(), "--", filename],
        capture_output=True,
    )

    origin_file = File(file_path=filename)
    new_line_list = []
    # 首先将最后一个 patch 以 flag=True 的方式 apply
    from_commit_sha = sha_list.pop()
    assert from_commit_sha == from_commit
    typer.echo(f"Apply patch {from_commit_sha} to {filename}")
    patch_path = os.path.join(
        BASE_DIR, PATCH_STORE_DIR, f"{from_commit_sha}-{process_title(filename)}.patch"
    )

    for diff in whatthepatch.parse_patch(
        open(patch_path, mode="r", encoding="utf-8").read()
    ):
        if diff.header.old_path == filename or diff.header.new_path == filename:
            try:
                new_line_list, _ = apply_change(
                    diff.changes, origin_file.line_list, flag=True
                )
            except Exception as e:
                typer.echo(f"Failed to apply patch {from_commit_sha}")
                typer.echo(f"Error: {e}")
                return
        else:
            typer.echo(f"Do not match with {filename}, skip")

    confict_list: list[list[Line]] = []

    # 注意这里需要反向
    sha_list.reverse()
    for sha in sha_list:
        patch_path = os.path.join(
            BASE_DIR, PATCH_STORE_DIR, f"{sha}-{process_title(filename)}.patch"
        )

        flag_line_list = []
        with open(patch_path, mode="r", encoding="utf-8") as (f):
            diffes = whatthepatch.parse_patch(f.read())

            for diff in diffes:
                if diff.header.old_path == filename or diff.header.new_path == filename:
                    try:
                        new_line_list, flag_line_list = apply_change(
                            diff.changes, new_line_list
                        )
                        typer.echo(
                            f"Apply patch {sha} to {filename}: {len(new_line_list)}"
                        )
                    except Exception as e:
                        typer.echo(f"Failed to apply patch {sha}")
                        typer.echo(f"Error: {e}")

                        with open(
                            filename + f".{sha}", mode="w+", encoding="utf-8"
                        ) as (f):
                            for line in new_line_list:
                                if line.status:
                                    f.write(line.content + "\n")

                        return
                else:
                    typer.echo(f"Do not match with {filename}, skip")

        assert isinstance(flag_line_list, list)

        if len(flag_line_list) > 0:
            confict_list.append(flag_line_list)
            typer.echo(f"Conflict found in {sha}")
            for line in flag_line_list:
                typer.echo(f"{line.index + 1}: {line.content}")

    # 写入文件
    with open(filename, mode="w+", encoding="utf-8") as (f):
        for line in new_line_list:
            if line.status:
                f.write(line.content + "\n")

    with open(filename + ".ppatch", mode="a+", encoding="utf-8") as (f):
        for line in new_line_list:
            if line.status:
                f.write(f"{line.index + 1}: {line.content} {line.flag}\n")

    typer.echo(f"Conflict count: {len(confict_list)}")
    typer.echo(f"Conflict list: {confict_list}")


@app.command()
def apply(filename: str, patch_path: str):
    """
    Apply a patch to a file.
    """
    if not os.path.exists(filename):
        typer.echo(f"Warning: {filename} not found!")
        return

    if not os.path.exists(patch_path):
        typer.echo(f"Warning: {patch_path} not found!")
        return

    typer.echo(f"Apply patch {patch_path} to {filename}")

    origin_file = File(file_path=filename)
    new_line_list = origin_file.line_list

    with open(patch_path, mode="r", encoding="utf-8") as (f):
        diffes = whatthepatch.parse_patch(f.read())

        for diff in diffes:
            if diff.header.old_path == filename or diff.header.new_path == filename:
                new_line_list, _ = apply_change(diff.changes, new_line_list)
            else:
                typer.echo(f"Do not match with {filename}, skip")
    # new_line_list, _ = _apply(patch_path, filename, new_line_list, "default")

    # 写入文件
    with open(filename, mode="w+", encoding="utf-8") as (f):
        for line in new_line_list:
            if line.status:
                f.write(line.content + "\n")


@app.command()
def getpatches(filename: str, expression: str = None, save: bool = True):
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

        if pattern is not None and pattern.search(patch) is not None:
            typer.echo(f"Patch {sha} found with expression {expression}")

        patch_path = os.path.join(
            BASE_DIR, PATCH_STORE_DIR, f"{sha}-{process_title(filename)}.patch"
        )

        if save:
            if not os.path.exists(patch_path):
                with open(patch_path, mode="w+", encoding="utf-8") as (f):
                    f.write(patch)
