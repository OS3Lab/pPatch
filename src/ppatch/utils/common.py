import fnmatch
import json
import re
import subprocess
from collections import defaultdict
from typing import Any

from ppatch.app import logger
from ppatch.model import CommandResult, CommandType, Line
from ppatch.utils.ast import File as FileAST
from ppatch.utils.ast import Func


def clean_repo():
    output = subprocess.run(["git", "clean", "-df"], capture_output=True).stdout.decode(
        "utf-8"
    )
    logger.debug(output)

    output = subprocess.run(
        ["git", "reset", "--hard"], capture_output=True
    ).stdout.decode("utf-8")
    logger.debug(output)


def process_title(filename: str):
    """
    Process the file name to make it suitable for path
    """
    return "".join([letter for letter in filename if letter.isalnum()])


def process_file_path(file_path: str, reverse: bool = False) -> str:
    """
    Process the file path to make it suitable for path
    """
    if reverse:
        return file_path.replace("&#", "/")  # Do not use _ here
    else:
        return file_path.replace("/", "&#")


def find_list_positions(main_list: list[str], sub_list: list[str]) -> list[int]:
    sublist_length = len(sub_list)
    positions = []

    for i in range(len(main_list) - sublist_length + 1):
        if main_list[i : i + sublist_length] == sub_list:
            positions.append(i)

    return positions


def isnamedtupleinstance(x):
    _type = type(x)
    bases = _type.__bases__
    if len(bases) != 1 or bases[0] != tuple:
        return False
    fields = getattr(_type, "_fields", None)
    if not isinstance(fields, tuple):
        return False
    return all(type(i) == str for i in fields)


def unpack(obj):
    if isinstance(obj, dict):
        return {key: unpack(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [unpack(value) for value in obj]
    elif isnamedtupleinstance(obj):
        return {key: unpack(value) for key, value in obj._asdict().items()}
    elif isinstance(obj, tuple):
        return tuple(unpack(value) for value in obj)
    else:
        return obj


def post_executed(executed_command_result: CommandResult | Any, **kwargs) -> None:
    """Executed command result callback function"""
    if type(executed_command_result) != CommandResult:
        return

    logger.debug(f"Executed {executed_command_result.type}")

    match executed_command_result.type:
        case CommandType.AUTO:
            clean_repo()
        case _:
            pass


def process_json_config(input_file: str) -> dict[str:list]:
    """
    Process the Compiler Output JSON file and extract the symbols
    """
    # 读取现有的 JSON 文件
    with open(input_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    # 提取所需的数据
    new_data = []
    for item in data:
        kind = item.get("kind")
        message = item.get("message")
        file_name = None
        if "locations" in item and item["locations"]:
            file_name = item["locations"][0]["caret"]["file"]

        if kind == "error" and message and file_name:
            # 使用正则表达式提取变量
            symbols = re.findall(r"‘(.*?)’", message)
            symbols.extend(re.findall(r"'(.*?)'", message))  # When to use ``?

            new_data.append(
                {
                    "kind": kind,
                    "file": file_name,
                    "message": message,
                    "symbol": symbols if symbols else None,
                }
            )

    # 使用 defaultdict 合并 symbol 列表
    merged_data = defaultdict(set)
    for item in new_data:
        file_name = item.get("file")
        symbols = item.get("symbol", [])
        if file_name:
            if symbols is None:
                symbols = []
            merged_data[file_name].update(symbols)

    # 将合并后的数据转换为字典格式
    result = {file: list(symbols) for file, symbols in merged_data.items()}

    return result


def match_file_patterns(filename: str, patterns: list[str]) -> bool:
    """
    Check if the filename matches any of the patterns

    Args:
        filename: file name
        patterns: list of wildcard patterns

    Returns:
        Returns True if the filename matches any pattern, otherwise returns False
    """
    return any(fnmatch.fnmatch(filename, pattern) for pattern in patterns)


def get_changed_funcs(line_list: list[Line], file_ast: FileAST) -> list[Func]:
    """
    line_list: list of changed lines, each line is a Line object with .changed attribute
    file_ast: FileAST object representing the file's AST
    """

    changed_lines: list[Line] = [line for line in line_list if line.changed]
    changed_funcs: list[Func] = []

    for line in changed_lines:
        line_number = line.index + 1

        func: Func | None = file_ast.locate_line(line_number)
        if func:
            changed_funcs.append(func)

    # TODO: 简化
    sorted_changed_funcs = []
    for func in changed_funcs:
        if func not in sorted_changed_funcs:
            sorted_changed_funcs.append(func)

    changed_funcs = sorted_changed_funcs

    return changed_funcs
