import os
import subprocess
from typing import Annotated

import typer

from ppatch.app import app, logger
from ppatch.commands.get import getpatches
from ppatch.config import settings
from ppatch.model import SHA, File
from ppatch.utils.ast import File as FileAST
from ppatch.utils.common import get_changed_funcs, process_title
from ppatch.utils.parse import parse_patch
from ppatch.utils.resolve import apply_change


@app.command()
def apply(
    # filename: str,
    patch_path: str,
    reverse: Annotated[bool, typer.Option("-R", "--reverse")] = False,
    fuzz: Annotated[int, typer.Option("-F", "--fuzz")] = 0,
    function_check: bool = typer.Option(False, "--function-check", "-f"),
):
    """
    Apply a patch to a file.
    """

    if not os.path.exists(patch_path):
        logger.error(f"Warning: {patch_path} not found!")
        raise typer.Exit(code=1)

    if reverse:
        logger.info("Reversing patch...")

    has_failed = False

    with open(patch_path, mode="r", encoding="utf-8") as (f):
        parser = parse_patch(f.read())
        diffes = parser.diff
        sha_list: list[SHA] = []

        if function_check:
            file_name = diffes[0].header.old_path  # No need to distinguish reverse here

            subject = parser.subject
            hit_list, sha_list = getpatches(file_name, subject, save=True)
            sha_for_sure = None

            for sha in hit_list:
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

                    # logger.debug(f"1st: {parse_patch(text).subject}")
                    # logger.debug(f"2nd: {subject}")

                    target_subject = parse_patch(text).subject
                    if target_subject in subject or subject in target_subject:
                        sha_for_sure = sha
                        break

            if sha_for_sure is None:
                logger.error(
                    f"function_check: Cannot find a patch with subject '{subject}' for file '{file_name}'."
                )
                raise typer.Exit(code=1)

        for diff in diffes:

            old_filename = diff.header.old_path
            new_filename = diff.header.new_path
            if reverse:
                old_filename, new_filename = new_filename, old_filename

            if os.path.exists(old_filename):

                logger.info(f"Applying patch to {old_filename}...")

                new_line_list = File(file_path=old_filename).line_list
                apply_result = apply_change(
                    diff.hunks, new_line_list, reverse=reverse, fuzz=fuzz
                )
                new_line_list = apply_result.new_line_list

                # 检查失败数
                for failed_hunk in apply_result.failed_hunk_list:
                    has_failed = True
                    logger.error(f"Failed hunk: {failed_hunk.index}")
            else:
                logger.error(f"{old_filename} not found!")

                # git log --oneline --diff-filter=R -- <old_filename>
                output: str = subprocess.run(
                    ["git", "log", "--oneline", "--diff-filter=R", "--", old_filename],
                    capture_output=True,
                ).stdout.decode("utf-8", errors="ignore")
                if len(output) > 0:
                    logger.warning(f"File {old_filename} has been renamed.")

                raise typer.Exit(code=2)

            # 写入文件
            if not has_failed:
                if function_check:
                    # Note that file won't be saved if function_check is True

                    # 记录当前修改所属的函数列表和所有函数列表
                    patched_text = "\n".join([line.content for line in new_line_list])
                    file_ast = FileAST(patched_text)

                    patched_all_funcs = file_ast.funcs
                    patched_changed_funcs = get_changed_funcs(new_line_list, file_ast)

                    # Get to the original file
                    # git show sha:filename
                    # 利用 sha_for_sure 获取指定 sha 的前一个 sha
                    sha_for_sure_index = sha_list.index(sha_for_sure)
                    sha_before_sure = sha_list[
                        sha_for_sure_index + 1
                    ]  # TODO: check this

                    before_original_file: str = subprocess.run(
                        [
                            "git",
                            "show",
                            f"{sha_before_sure}:{diff.header.old_path}",
                        ],  # No need to distinguish reverse here
                        capture_output=True,
                    ).stdout.decode("utf-8", errors="ignore")

                    # 尝试 apply 原补丁来确定原始修改所属的函数
                    original_file_line_list = apply_change(
                        diff.hunks,
                        File(content=before_original_file).line_list,
                        reverse=reverse,
                        fuzz=fuzz,
                    ).new_line_list

                    original_file_ast = FileAST(before_original_file)
                    original_changed_funcs = get_changed_funcs(
                        original_file_line_list, original_file_ast
                    )

                    logger.info(f"Patched changed funcs: {patched_changed_funcs}")
                    logger.info(f"Original changed funcs: {original_changed_funcs}")

                with open(new_filename, mode="w+", encoding="utf-8") as f:
                    for line in new_line_list:
                        if line.status:
                            f.write(line.content + "\n")

    raise typer.Exit(code=1 if has_failed else 0)
