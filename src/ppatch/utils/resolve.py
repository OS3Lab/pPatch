from whatthepatch.patch import Change

from ppatch.model import File, Line


def apply_change(
    changes: list[Change], target: list[Line], flag: bool = False
) -> list[Line]:
    """Apply a diff to a target string."""

    for change in changes:
        if change.old == change.new:
            continue

        if change.old is None:
            # 在 File 中找到 index 为 change.new 的行，且当前标记为 False 的行，在这行前添加 change.line
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

    # 保留所有 status 为 Ture 的行
    new_line_list = []
    for index, line in enumerate(target):
        if line.status:
            new_line_list.append(
                Line(index=index, content=line.content + "\n", changed=line.changed)
            )

    # # 将 new_line_list 写入文件
    # with open(target + ".bak", mode="w", encoding="utf-8") as f:
    #     for line in new_line_list:
    #         f.write(line.content)

    return new_line_list
