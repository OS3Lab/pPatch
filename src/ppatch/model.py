from pydantic import BaseModel


class Line(BaseModel):
    index: int
    content: str
    changed: bool = False
    status: bool = True
    flag: bool = False

    def __str__(self) -> str:
        return self.content


class File(object):
    def __init__(self, file_path: str) -> None:
        self.line_list: list[Line] = []

        with open(file_path, mode="r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                self.line_list.append(Line(i, line.rstrip("\n")))
