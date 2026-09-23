# input 1: current file
# input 2: current patch
# input 3: original file
# input 4: original patch

from ppatch.model import File, Patch
from ppatch.utils.ast import File as FileAST
from ppatch.utils.ast import Func
from ppatch.utils.parse import parse_patch

file_path = ""

original_file = ""
original_patch = ""

current_file = ""
current_patch = ""


def find_changed_funcs(file: str, patch: str) -> list[Func]:

    original_lines = File(content=file).line_list
    current_patch: Patch = parse_patch(patch)

    # 从 Patch 确定要产生修改的行
    # 前提在于选定的 patch 是正确的（如何保证呢，需要使用 Diff）
    current_diff = None

    for diff in current_patch.diff:
        if diff.header.old_path == file_path:
            current_diff = diff
            break

    changed_lines = []
    for change in current_diff.changes:
        if change.old is not None:
            original_lines[change.old].changed = True
            changed_lines.append(change.old)

    ast_file = FileAST("".join([str(line) + "\n" for line in original_lines]))

    changed_funcs: list[Func] = []
    for line in changed_lines:
        func = ast_file.line_func_map[line]
        if func and func not in changed_funcs:
            changed_funcs.append(func)

    return changed_funcs


def check(
    original_file: str, original_patch: str, current_file: str, current_patch: str
):

    old_changed_funcs = find_changed_funcs(original_file, original_patch)
    new_changed_funcs = find_changed_funcs(current_file, current_patch)

    old_funcs = FileAST(original_file).funcs
    # new_funcs = FileAST(current_file).funcs

    old_changed_func_names = [func["name"] for func in old_changed_funcs]
    old_func_names = [func["name"] for func in old_funcs]

    new_changed_func_names = [func["name"] for func in new_changed_funcs]
    new_func_names = [func["name"] for func in FileAST(current_file).funcs]

    for func in new_changed_funcs:
        if func["name"] not in old_changed_func_names:
            print(f"Warning: found new changed function {func['name']}")
            # Check if the function actually exists in the old file
            if func["name"] in old_func_names:
                print(f"Warning: found inconsistent changed function {func['name']}")

    # for func in old_changed_funcs:
    #     if func["name"] not in new_changed_func_names:
    #         print(f"Warning: found missing changed function {func['name']}")
    #         # Check if the function actually exists in the new file
    #         if func["name"] not in new_func_names:
    #             print(f"Warning: found inconsistent changed function {func['name']}")

    # for func in old_funcs:
    #     if func["name"] == "hci_get_route" or func["name"] == "hci_conn_enter_active_mode":
    #         print(f"Warning: found changed function {func['name']}")


check(original_file, original_patch, current_file, current_patch)
