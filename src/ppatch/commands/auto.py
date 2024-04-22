import os
import re
import subprocess

import typer

from ppatch.app import app
from ppatch.commands.get import getpatches
from ppatch.commands.trace import trace
from ppatch.config import settings
from ppatch.model import ApplyResult, Diff, File, Line
from ppatch.utils.common import process_title
from ppatch.utils.parse import parse_patch


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

    # 防呆设计
    # To do 添加 - n 交互
    output_parts = [part for part in output_parts if "Ignore -R" not in part]
    if len(output_parts) == 0:
        typer.echo("Unreversed patch detected!")
        raise typer.Exit()

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
                    settings.base_dir,
                    settings.patch_store_dir,
                    f"{sha}-{process_title(file_name)}.patch",
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

        # hunklist [1,2,3]
        # ApplyResult = trace(hunklist)
        # ApplyResult => {sha: ApplyResult}
        # trace
        # ApplyResult => trace(ApplyResult.flag_line_list.hunk)
        # ApplyResult => {sha: dict[sha,ApplyResult]}
        recursive_apply_result: dict[str, list[dict[str, list[ApplyResult]]]] = {}
        for hunk in hunk_list:
            apply_result = trace(file_name, from_commit=sha_for_sure, flag_hunk=hunk)
            # recursive(file_name,apply_result)
            for sha, patch_result in apply_result.items():
                typer.echo(f"Sha: {sha}")
                if sha not in recursive_apply_result:
                    recursive_apply_result[sha] = []
                if len(patch_result.flag_line_list) != 0:
                    typer.echo(f"Value: {patch_result.flag_line_list}")
                    hunk_list = list(
                        set(
                            item.hunk
                            for item in patch_result.flag_line_list
                            if item.hunk is not None
                        )
                    )
                    for hunk in hunk_list:
                        # recursive(file_name,apply_result,recursive_apply_result)
                        recursive_apply_result[sha].append(
                            trace(file_name, from_commit=sha, flag_hunk=hunk)
                        )

        # ApplyResult => {sha: list[ApplyResult]}
        # sha_list :list[str] = []
        typer.echo(f"filename:{filename}")
        for sha, patch_result in recursive_apply_result.items():
            # typer.echo(f"Sha_echo: {sha}")
            for patch_result2 in patch_result:
                # typer.echo("in patch_result2")
                for sha, patch_result in patch_result2.items():
                    if len(patch_result.flag_line_list) != 0:
                        hunk_list = list(
                            set(
                                item.hunk
                                for item in patch_result.flag_line_list
                                if item.hunk is not None
                            )
                        )
                        for hunk in hunk_list:
                            typer.echo(f"Sha_flag: {sha}: Hunk_flag: {hunk}")
                            recursive_apply_result[sha].append(
                                trace(file_name, from_commit=sha, flag_hunk=hunk)
                            )
                            # apply_result3 = trace(file_name,from_commit=sha,flag_hunk=hunk)
                            # print_recursive_apply_result(apply_result3)
                    else:
                        typer.echo(f"Sha_no_flag: {sha}: Hunk_no_flag: None")
                        # apply_result3 = trace(file_name,from_commit=sha)
                        # print_recursive_apply_result(apply_result3)


def recursive(
    file_name, apply_result, recursive_apply_result: dict[str, list[ApplyResult]]
):
    for sha, patch_result in apply_result.items():
        typer.echo(f"Sha_recursive: {sha}")
        if len(patch_result.flag_line_list) != 0:
            typer.echo(f"Value_recursive: {patch_result.flag_line_list}")
            hunk_list = list(
                set(
                    item.hunk
                    for item in patch_result.flag_line_list
                    if item.hunk is not None
                )
            )
            typer.echo(f"recursive Hunk_list: {hunk_list}")
            if len(hunk_list) == 0:
                typer.echo(f"hunk_list is none")
                return recursive_apply_result[sha].append(
                    trace(file_name, from_commit=sha)
                )
            for hunk in hunk_list:
                apply_result2 = trace(file_name, from_commit=sha, flag_hunk=hunk)
                typer.echo(f"Sha2: {sha}: Hunk2: {hunk}")
                return recursive(file_name, apply_result2, recursive_apply_result)
        else:
            continue


def print_recursive_apply_result(apply_result3):
    for sha, patch_result in apply_result3.items():
        typer.echo(f"Sha3: {sha}")
        if len(patch_result.flag_line_list) != 0:
            typer.echo(f"Value3: {patch_result.flag_line_list}")
            hunk_list = list(
                set(
                    item.hunk
                    for item in patch_result.flag_line_list
                    if item.hunk is not None
                )
            )
            for hunk in hunk_list:
                typer.echo(f"Sha3: {sha}: Hunk3: {hunk}")
