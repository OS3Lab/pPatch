from pydantic import BaseModel
from whatthepatch.patch import Change


class Line(BaseModel):
    index: int
    content: str
    changed: bool = False  # 标识在一轮 apply 中是否进行了修改
    status: bool = True  # 标识在一轮 apply 中是否被删除
    flag: bool = False  # 标识是否是在初次标记中修改了的行

    def __str__(self) -> str:
        return self.content


class File(object):
    def __init__(self, file_path: str) -> None:
        self.line_list: list[Line] = []

        with open(file_path, mode="r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                self.line_list.append(Line(index=i, content=line.rstrip("\n")))

    def __str__(self) -> str:
        return "".join([str(line) for line in self.line_list])


class Hunk(BaseModel):
    index: int
    context: list[Change]
    middle: list[Change]
    post: list[Change]

    all_: list[Change]
