from whatthepatch.patch import Change

from ppatch.model import Hunk, Line
from ppatch.utils.common import find_list_positions


def apply_change(
    changes: list[Change], target: list[Line], flag: bool = False
) -> tuple[list[Line], list[Line]]:
    """Apply a diff to a target string."""

    # TODO: 这里有个巨大的问题：diff 信息中的行号与实际行号不一致
    # 一种修复方式：搜索 diff 每个 hunk 的上下文行，然后修改标记

    # 首先统计 Hunk 数
    hunk_indexes = []
    for change in changes:
        if change.hunk not in hunk_indexes:
            hunk_indexes.append(change.hunk)

    # TODO: 支持 -F 参数
    # 将changes按照hunk分组，注意同一个 hunk 中的 change 要进行分类，前三行要放入前置上下文，中间的要放入中间上下文，后三行要放入后置上下文
    hunk_list: list[Hunk] = []
    for hunk_index in hunk_indexes:
        hunk_changes = [change for change in changes if change.hunk == hunk_index]

        # 这里遍历的顺序已经是正确的顺序
        hunk_context = []
        hunk_middle = []
        hunk_post = []
        # 首先正向遍历，获取前置上下文
        for change in hunk_changes:
            if change.old is not None and change.new is not None:
                hunk_context.append(change)
            else:
                break

        # 然后反向遍历，获取后置上下文
        for change in reversed(hunk_changes):
            if change.old is not None and change.new is not None:
                hunk_post.append(change)
            else:
                break

        # 注意把后置上下文反转回来
        hunk_post = list(reversed(hunk_post))

        # 最后获取中间上下文
        for change in hunk_changes:
            if change not in hunk_context and change not in hunk_post:
                hunk_middle.append(change)

        hunk_list.append(
            Hunk(
                index=hunk_index,
                context=hunk_context,
                middle=hunk_middle,
                post=hunk_post,
                all_=hunk_changes,
            )
        )

    # 然后对每个hunk进行处理，添加偏移
    changes: list[Change] = []
    for hunk in hunk_list:

        def cal_offsets(target: list[Line], changes: list[Change]) -> list[int]:
            pos_list = find_list_positions(
                [line.content for line in target],
                [change.line for change in changes],
            )
            if len(pos_list) == 0:
                raise Exception(f"context lines do not exist in source")

            offset_list = []
            if len(changes) == 0:
                offset_list = pos_list
            else:
                for position in pos_list:
                    offset = position + 1 - changes[0].old
                    offset_list.append(offset)

            return offset_list

        offset_context = cal_offsets(target, hunk.context)
        offset_post = cal_offsets(target, hunk.post)

        offset_list = list(set(offset_context) & set(offset_post))
        if len(offset_list) == 0:
            raise Exception("offsets do not intersect")

        # 计算最小 offset
        min_offset = None
        for offset in offset_list:
            if min_offset is None or abs(offset) < abs(min_offset):
                min_offset = offset

        for change in hunk.all_:
            changes.append(
                Change(
                    hunk=change.hunk,
                    old=change.old + min_offset if change.old is not None else None,
                    new=change.new + min_offset if change.new is not None else None,
                    line=change.line,
                )
            )

    # 注意这里的 changes 应该使用从 hunk_list 中拼接出来的（也就是修改过行号的）
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

    flag_line_list = []
    add_count = 0
    del_count = 0

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
