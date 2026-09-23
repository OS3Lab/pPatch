import os
import subprocess

import typer

from ppatch.app import app, logger
from ppatch.commands.get import getpatches
from ppatch.commands.symbol import getsymbol_from_patch
from ppatch.commands.trace import trace
from ppatch.config import settings
from ppatch.model import (
    FILENAME,
    SHA,
    ApplyResult,
    CommandResult,
    CommandType,
    Diff,
    File,
)
from ppatch.utils.ast import File as FileAST
from ppatch.utils.ast import Func
from ppatch.utils.common import (
    get_changed_funcs,
    match_file_patterns,
    process_json_config,
    process_title,
)
from ppatch.utils.parse import changes_to_hunks, parse_patch
from ppatch.utils.resolve import apply_change


def process_str(s: str) -> str:
    return "".join(c if c.isalnum() or c == "_" else "_" for c in s)


@app.command()
def auto(
    filename: str,
    output: str = typer.Option("", "--output", "-o"),
    extra_config: str = typer.Option("", "--extra-config", "-c"),
    use_multi_file: bool = typer.Option(False, "--multi-file", "-m"),
    oracle: bool = typer.Option(False, "--oracle", "-O"),
):
    """Automatic do ANYTHING"""
    if not os.path.exists(filename):
        logger.error(f"{filename} not found!")

        return CommandResult(
            type=CommandType.AUTO,
        )

    if not os.path.exists(output) and not output.endswith(".patch"):
        logger.error(f"output {output} not found!")
        return CommandResult(
            type=CommandType.AUTO,
        )

    if os.path.isdir(output):
        output = os.path.join(output, "auto.patch")

    content = ""
    with open(filename, mode="r", encoding="utf-8", errors="ignore") as (f):
        content = f.read()

    parser = parse_patch(content)
    fail_file_list: dict[str, list[int]] = {}  # filename: [hunk.index]
    diffes: list[Diff] = parser.diff
    for diff in diffes:
        target_file = diff.header.new_path  # 这里注意是 new_path 还是 old_path

        # 检查文件是否符合 include_file_list 中的通配符
        if not match_file_patterns(target_file, settings.include_file_list):
            logger.info(
                f"Skipping file {target_file} as it does not match include patterns"
            )
            continue

        if not os.path.exists(target_file):
            logger.error(f"File {target_file} not found!")
            return CommandResult(
                type=CommandType.AUTO,
            )

        origin_file = File(file_path=target_file)

        # 执行 Reverse，确定失败的 Hunk
        apply_result = apply_change(
            diff.hunks,
            origin_file.line_list,
            reverse=True,
            fuzz=2,  # TODO: 调整为 fuzz=2，还需要改 trace 里的 fuzz 参数
        )

        if len(apply_result.failed_hunk_list) != 0:
            logger.info(f"Failed hunk in {target_file}")
            fail_file_list[target_file] = [
                hunk.index for hunk in apply_result.failed_hunk_list
            ]

    if len(fail_file_list) == 0:
        logger.info("No failed patch")

        return CommandResult(
            type=CommandType.AUTO,
        )

    subject = parser.subject
    diffes: list = []
    filename_with_conflict_list: dict[FILENAME, list[tuple[SHA, ApplyResult]]] = {}

    symbols: list[str] = None
    if extra_config != "":
        logger.info(f"Using extra config {extra_config}")
        # with open(extra_config, mode="r", encoding="utf-8") as (extra_config_file):
        # extra_config_json: list | dict = json.load(extra_config_file)

        extra_config_json = process_json_config(extra_config)
        symbols = [
            item
            for value in extra_config_json.values()
            if isinstance(value, list)
            for item in value
        ]

        logger.debug(f"Symbols to search: {symbols}")

    for file_name, hunk_list in fail_file_list.items():
        logger.info(
            f"{len(hunk_list)} hunk(s) failed in {file_name} with subject {subject}"
        )

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
            logger.error(f"No patch found for {file_name}")

            return CommandResult(
                type=CommandType.AUTO,
            )

        logger.info(f"Found correspond patch {sha_for_sure} to {file_name}")
        logger.info(f"Hunk list: {hunk_list}")

        conflict_list = trace(
            sha_list,
            file_name,
            commits=[sha_for_sure],
            flag_hunks_list=[hunk_list],
            symbols=symbols,
        )

        conflict_list = list(conflict_list.items())
        conflict_list.reverse()

        filename_with_conflict_list[file_name] = conflict_list

    if extra_config != "" and use_multi_file:
        logger.info("Searching Symbols in extra files (Symbol Mode II)")

        # 收集所有已发现冲突的 SHA
        conflict_shas = set()
        for file_conflicts in filename_with_conflict_list.values():
            for sha, _ in file_conflicts:
                conflict_shas.add(sha)

        # 对每个 SHA，获取其他包含 symbol 的文件
        new_files_to_trace: dict[FILENAME, list[tuple[SHA, list[int]]]] = {}

        for sha in conflict_shas:
            patch_path = os.path.join(
                settings.base_dir,
                settings.patch_store_dir,
                f"{sha}.patch",
            )

            if not os.path.exists(patch_path):
                # Get patch from repository using git show
                _output = subprocess.run(
                    ["git", "show", sha],
                    capture_output=True,
                ).stdout.decode("utf-8", errors="ignore")

                with open(patch_path, "w", encoding="utf-8") as f:
                    f.write(_output)

            # 获取该 patch 中所有包含 symbol 的文件和对应的 hunks
            symbol_files = getsymbol_from_patch(patch_path, symbols)

            # 对每个新发现的文件
            for file_name, hunks in symbol_files.items():
                if file_name not in filename_with_conflict_list:  # 仅处理尚未处理的文件
                    if file_name not in new_files_to_trace:
                        new_files_to_trace[file_name] = []
                    new_files_to_trace[file_name].append((sha, hunks))

        # 对新文件执行 trace
        for file_name, sha_hunks in new_files_to_trace.items():
            if not os.path.exists(file_name):
                logger.warning(f"File {file_name} not found, skipping")
                continue

            commits = []
            flag_hunks_list = []
            for sha, hunks in sha_hunks:
                commits.append(sha)
                flag_hunks_list.append(hunks)

            # 获取文件的历史记录
            _, sha_list = getpatches(file_name, None, save=True)

            # 执行 trace
            conflict_list = trace(
                sha_list,
                file_name,
                commits=commits,
                flag_hunks_list=flag_hunks_list,
                symbols=symbols,
            )

            if conflict_list:  # 只添加有冲突的结果
                conflict_list = list(conflict_list.items())
                conflict_list.reverse()
                filename_with_conflict_list[file_name] = conflict_list
                logger.info(
                    f"Added new file {file_name} with {len(conflict_list)} conflicts"
                )

    planned_hunks_count: int = 0
    # added_hunks_count: int = 0
    for file_name, conflict_list in filename_with_conflict_list.items():

        line_list = File(file_path=file_name).line_list

        for sha, apply_result in conflict_list:
            # 对 apply_result.failed_hunk_list 中的冲突块按照 hunk.index 进行排序
            apply_result.failed_hunk_list = sorted(
                apply_result.failed_hunk_list, key=lambda x: x.index
            )

            logger.info(
                f"Conflict hunk in {sha}: {[hunk.index for hunk in apply_result.failed_hunk_list]}"
            )

            changes = []
            for hunk in apply_result.failed_hunk_list:
                changes.extend(hunk.all_)
                planned_hunks_count += 1

            _apply_result = apply_change(
                changes_to_hunks(changes), line_list, reverse=True, fuzz=3, flag=True
            )
            # TODO: 错误处理
            try:
                assert len(_apply_result.failed_hunk_list) == 0
            except AssertionError:
                logger.error(
                    f"AUTO: Failed hunk in {sha}; len: {len(_apply_result.failed_hunk_list)}"
                )
                planned_hunks_count -= len(_apply_result.failed_hunk_list)

            line_list = _apply_result.new_line_list

        origin_file = File(file_path=file_name)
        patched_text = "\n".join([line.content for line in line_list])
        origin_text = "\n".join([line.content for line in origin_file.line_list])

        # 在 patched_text 上进行修改
        # 1. 获取所有发生变更的行的行号和 hunk.index
        # 2. 搜索这些行在在 patched_text 中属于哪些函数的范围，如果不是函数则不处理
        # 3. 在这些函数的起始位置添加 printk
        if oracle:
            file_ast = FileAST(content=patched_text)

            changed_funcs: list[Func] = get_changed_funcs(line_list, file_ast)

            for func in changed_funcs:
                # 从 start_line 开始读取，读取到的第一个 '{' 之后插入一行 printk
                patched_lines = patched_text.splitlines()
                # convert to 0-based index
                start_idx = func["start_line"] - 1
                # 从函数定义开始位置往后找第一个 '{'
                for i in range(start_idx, len(patched_lines)):
                    if "{" in patched_lines[i]:
                        patched_lines.insert(
                            i + 1,
                            f"""\tprintk(KERN_NOTICE "PPATCH {process_str(func["name"])} {filename.split("/")[-1]}\\n");""",
                        )
                        break
                # 重新构建 patched_text
                patched_text = "\n".join(patched_lines)

        import difflib

        diffes_ = difflib.unified_diff(
            origin_text.splitlines(),
            patched_text.splitlines(),
            fromfile="a/" + file_name,
            tofile="b/" + file_name,
        )

        for line in diffes_:
            diffes.append(line + "\n" if not line.endswith("\n") else line)

    with open(
        output,
        mode="w+",
        encoding="utf-8",
    ) as (f):
        patch_content = "".join(diffes)
        if len(patch_content) == 0:
            logger.error("No patch generated")
            return CommandResult(
                type=CommandType.AUTO,
            )

        f.write(patch_content)
        logger.info(
            # f"Hunks planned: {planned_hunks_count} Hunk added: {added_hunks_count}"
            f"Hunks planned: {planned_hunks_count}"
        )
        logger.info(f"Patch file generated: {output}")

    return CommandResult(
        type=CommandType.AUTO,
    )
