import os
import re

from cscopy.cli import CscopeCLI
from cscopy.model import SearchResult
from cscopy.workspace import CscopeWorkspace

from ppatch.app import app, logger
from ppatch.model import Diff
from ppatch.utils.common import process_file_path
from ppatch.utils.parse import parse_patch


@app.command("symbol")
def getsymbol_command(
    file: str,
    symbols: list[str] = [],
):
    getsymbol(file, symbols)


def getsymbol(file: str, symbols: list[str]) -> dict[str, list[SearchResult]]:
    logger.debug(f"Getting symbols from {file} with {symbols}")

    cli = CscopeCLI("/usr/bin/cscope")

    files: list[str] = []

    # 针对 patch 类型的文件需要进行特殊处理
    if file.endswith(".patch"):
        diffes: list[Diff] = parse_patch(
            os.read(os.open(file, os.O_RDONLY), os.path.getsize(file)).decode(
                "utf-8", errors="ignore"
            )
        ).diff

        for diff in diffes:
            for hunk in diff.hunks:
                # add_path = f"/dev/shm/{index}-{hunk.index}-add"
                # del_path = f"/dev/shm/{index}-{hunk.index}-del"

                # with open(add_path, "w") as f:
                #     for change in hunk.middle:
                #         if change.new is not None and change.old is None:
                #             f.write(change.line + "\n")

                # with open(del_path, "w") as f:
                #     for change in hunk.middle:
                #         if change.new is None and change.old is not None:
                #             f.write(change.line + "\n")

                # files.append(add_path)
                # files.append(del_path)

                hunk_path = (
                    f"/dev/shm/{process_file_path(diff.header.new_path)}-{hunk.index}"
                )
                with open(hunk_path, "w") as f:
                    for change in hunk.middle:
                        if change.new is not None and change.old is None:
                            f.write(change.line + "\n")
                        if change.new is None and change.old is not None:
                            f.write(change.line + "\n")

                files.append(hunk_path)

    else:
        files = [file]

    res = {}
    with CscopeWorkspace(files, cli) as workspace:
        for symbol in symbols:
            result = workspace.search_c_symbol(symbol)
            res[symbol] = result

            for _res in result:
                logger.info(
                    f"{process_file_path(_res.file,reverse=True)}:{_res.line} {_res.content}"
                )

    if file.endswith(".patch"):
        for f in files:
            os.remove(f)

    return res


# TODO: 返回值的 diff_index 修改为 diff 对应的文件名
def getsymbol_from_patch(file: str, symbols: list[str]) -> dict[str, list[int]]:
    """
    Get symbols from a patch file

    Args:
        file (str): The patch file
        symbols (list[str]): The symbols to search
    Returns:
        diff_hunks (list[int]): hunk numbers of which the symbols are found
    """

    diff_hunks: dict[str, list[int]] = {}
    res = getsymbol(file, symbols)
    for search_res in res.values():
        for _res in search_res:
            # 按照 /dev/shm/{index}-{hunk.index} 的格式从 _res.file 中匹配出 diff index 和 hunk index
            match = re.match(r"/dev/shm/(.*?)-(\d+)", _res.file)
            if match:
                file_path = process_file_path(str(match.group(1)), reverse=True)
                hunk_index = int(match.group(2))

                # logger.info(f"Symbol found in {file_path} hunk {hunk_index}")

                if file_path not in diff_hunks:
                    diff_hunks[file_path] = []

                diff_hunks[file_path].append(hunk_index)

    return diff_hunks
