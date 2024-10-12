import os
import re

from cscopy.cli import CscopeCLI
from cscopy.model import SearchResult
from cscopy.workspace import CscopeWorkspace

from ppatch.app import app, logger
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
        diffes = parse_patch(
            os.read(os.open(file, os.O_RDONLY), os.path.getsize(file)).decode(
                "utf-8", errors="ignore"
            )
        ).diff

        for index, diff in enumerate(diffes):
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

                hunk_path = f"/dev/shm/{index}-{hunk.index}"
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
                logger.info(f"{_res.file}:{_res.line} {_res.content}")

    if file.endswith(".patch"):
        for f in files:
            os.remove(f)

    return res


def getsymbol_from_patch(file: str, symbols: list[str]) -> dict[int, list[int]]:
    """
    Get symbols from a patch file

    Args:
        file (str): The patch file
        symbols (list[str]): The symbols to search
    Returns:
        diff_hunks (list[int]): hunk numbers of which the symbols are found
    """

    diff_hunks: dict[int, list[int]] = {}
    res = getsymbol(file, symbols)
    for search_res in res.values():
        for _res in search_res:
            # 按照 /dev/shm/{index}-{hunk.index} 的格式从 _res.file 中匹配出 diff index 和 hunk index
            match = re.match(r"/dev/shm/(\d+)-(\d+)", _res.file)
            if match:
                diff_index = int(match.group(1))
                hunk_index = int(match.group(2))

                if diff_index not in diff_hunks:
                    diff_hunks[diff_index] = []

                diff_hunks[diff_index].append(hunk_index)

    return diff_hunks
