import os
import re
import subprocess

import typer
import whatthepatch

from .model import File, Line
from .utils.common import process_title
from .utils.parse import parse_patch
from .utils.resolve import apply_change

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

    patch = parse_patch(content)

    typer.echo(f"Patch: {filename}")
    typer.echo(f"Sha: {patch.sha}")
    typer.echo(f"Author: {patch.author}")
    typer.echo(f"Date: {(patch.date).strftime('%Y-%m-%d %H:%M:%S')}")
    typer.echo(f"Subject: {patch.subject}")

    for diff in patch.diff:
        typer.echo(f"Diff: {diff.header.old_path} -> {diff.header.new_path}")
        # for i, change in enumerate(diff.changes):
        #     typer.echo(f"{i+1}: {change.hunk}")


@app.command()
def trace(filename: str, from_commit: str = "", flag_hunk: int = -1):
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
    ).stdout.decode("utf-8", errors="ignore")

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
                    diff.changes, origin_file.line_list, flag=True, flag_hunk=flag_hunk
                )
            except Exception as e:
                typer.echo(f"Failed to apply patch {from_commit_sha}")
                typer.echo(f"Error: {e}")
                return
        else:
            typer.echo(f"Do not match with {filename}, skip")

    confict_list: dict[str, list[Line]] = {}

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
            confict_list[sha] = flag_line_list
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

    return confict_list


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
def getpatches(filename: str, expression: str = None, save: bool = True) -> list[str]:
    """
    Get patches of a file.
    """
    if not os.path.exists(filename):
        typer.echo(f"Warning: {filename} not found!")
        return

    typer.echo(f"Get patches of {filename}")

    output: str = subprocess.run(
        ["git", "log", "-p", "--", filename], capture_output=True
    ).stdout.decode("utf-8", errors="ignore")

    # 将 output 按照 commit ${hash}开头的行分割
    patches: list[str] = []
    for line in output.splitlines():
        if line.startswith("commit "):
            patches.append(line + "\n")
        else:
            patches[-1] += line + "\n"

    typer.echo(f"Get {len(patches)} patches for {filename}")

    pattern = re.compile(expression) if expression is not None else None

    sha_list = []
    for patch in patches:
        sha = patch.splitlines()[0].split(" ")[1]

        if pattern is not None and pattern.search(patch) is not None:
            sha_list.append(sha)
            typer.echo(f"Patch {sha} found with expression {expression}")

        patch_path = os.path.join(
            BASE_DIR, PATCH_STORE_DIR, f"{sha}-{process_title(filename)}.patch"
        )

        if save:
            if not os.path.exists(patch_path):
                with open(patch_path, mode="w+", encoding="utf-8") as (f):
                    f.write(patch)

    return sha_list


@app.command()
def auto(filename: str):
    """Automatic do ANYTHING"""
    if not os.path.exists(filename):
        typer.echo(f"Warning: {filename} not found!")
        return

    # "patch -R -p1 -F 3 -i {filename}"
    # TODO: 令 apply patch 支持 -R -F 参数，将此处切换为自行实现的版本
    output: str = subprocess.run(
        ["patch", "-R", "-p1", "-F", "3", "-i", filename], capture_output=True
    ).stdout.decode("utf-8", errors="ignore")

    # 首先按照 patching file，将输出分割为几块
    output_parts: list[str] = []
    for line in output.splitlines():
        if line.startswith("patching file "):
            output_parts.append(line + "\n")
        else:
            output_parts[-1] += line + "\n"

    output_parts = [part for part in output_parts if "FAILED" in part]
    if len(output_parts) == 0:
        typer.echo("No failed patch")
        return

    # 确定每个 Part 里，有哪些文件，第几个 hunk 失败了
    fail_file_list: dict[str, list[int]] = {}
    for part in output_parts:
        file_name = part.splitlines()[0].split(" ")[-1]

        fail_hunk_list = []
        for line in part.splitlines():
            # 使用正则表达式匹配 hunk
            # Hunk #1 FAILED at 1.
            match = re.search(r"Hunk #(\d+) FAILED at (\d+).", line)
            if match:
                fail_hunk_list.append(int(match.group(1)))

        fail_file_list[file_name] = fail_hunk_list

    content = ""
    with open(filename, mode="r", encoding="utf-8") as (f):
        content = f.read()

    from ppatch.utils.parse import parse_patch

    subject = parse_patch(content).subject
    for file_name, hunk_list in fail_file_list.items():
        typer.echo(
            f"{len(hunk_list)} hunk(s) failed in {file_name} with subject {subject}"
        )

        sha_list = getpatches(file_name, subject, save=True)
        sha_for_sure = None

        for sha in sha_list:
            with open(
                os.path.join(
                    BASE_DIR, PATCH_STORE_DIR, f"{sha}-{process_title(file_name)}.patch"
                ),
                mode="r",
                encoding="utf-8",
            ) as (f):
                text = f.read()
                if parse_patch(text).subject == subject:
                    sha_for_sure = sha
                    break

        if sha_for_sure is None:
            typer.echo(f"Error: No patch found for {file_name}")
            return

        typer.echo(f"Found correspond patch {sha_for_sure} to {file_name}")
        typer.echo(f"Hunk list: {hunk_list}")

        for hunk in hunk_list:
            conflict_list = trace(file_name, from_commit=sha_for_sure, flag_hunk=hunk)
            typer.echo(f"Conflict list: {conflict_list}")
