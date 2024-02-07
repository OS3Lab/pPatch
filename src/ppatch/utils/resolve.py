from whatthepatch.patch import Change

from ppatch.model import Line


def apply_change(
    changes: list[Change], target: list[Line], flag: bool = False
) -> tuple[list[Line], list[Line]]:
    """Apply a diff to a target string."""

    flag_line_list = []
    for change in changes:
        # 只修改新增行和删除行（只有这些行是被修改的）
        if change.old is None:
            # 在 File 中找到 index 为 change.new 的行，且当前 changed 为 False 的行，在这行前添加 change.line
            position = next(
                (
                    line
                    for line in target
                    if line.index == change.new - 1 and not line.changed
                ),
                None,
            )
            if position:
                target.insert(
                    position.index,
                    Line(
                        index=position.index,
                        content=change.line,
                        changed=True,
                        status=True,
                        flag=flag,
                    ),
                )
        elif change.new is None:
            # 找到 index 为 change.old 的行，将其移除
            position = next(
                (
                    line
                    for line in target
                    if line.index == change.old - 1 and not line.changed and line.status
                ),
                None,
            )
            if position:
                position.status = False

                # 如果被修改行有标记，则将其添加进标记列表
                if position.flag:
                    flag_line_list.append(position)

    # 保留所有 status 为 Ture 的行
    new_line_list = []
    for index, line in enumerate(target):
        if line.status:
            new_line_list.append(
                Line(index=index, content=line.content + "\n", changed=line.changed)
            )

    return new_line_list, flag_line_list
