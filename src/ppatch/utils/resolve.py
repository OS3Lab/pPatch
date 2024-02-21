from whatthepatch.patch import Change

from ppatch.model import Line


def apply_change(
    changes: list[Change], target: list[Line], flag: bool = False
) -> tuple[list[Line], list[Line]]:
    """Apply a diff to a target string."""

    flag_line_list = []
    add_count = 0
    del_count = 0

    # 检查被修改的行是否存在
    for change in changes:
        if change.old is not None and change.line is not None:
            if change.old > len(target):
                raise Exception(
                    f'context line {change.old}, "{change.line}" does not exist in source'
                )
            if target[change.old - 1].content != change.line:
                raise Exception(
                    f'context line {change.old}, "{change.line}" does not match "{target[change.old - 1]}"'
                )

    for change in changes:
        # 只修改新增行和删除行（只有这些行是被修改的）
        if change.old is None and change.new is not None:
            target.insert(
                change.new - 1,
                Line(
                    index=change.new - 1,
                    content=change.line,
                    changed=True,
                    status=True,
                    flag=flag,
                ),
            )
            add_count += 1

        elif change.new is None and change.old is not None:
            index = change.old - 1 - del_count + add_count

            # 如果被修改行有标记，则将其添加进标记列表
            if target[index].flag:
                flag_line_list.append(target[index])

            del target[index]
            del_count += 1

    new_line_list = []
    for index, line in enumerate(target):
        new_line_list.append(
            Line(
                index=index, content=line.content, changed=line.changed, flag=line.flag
            )
        )

    return new_line_list, flag_line_list
