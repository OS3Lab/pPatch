from typing import TypedDict

import tree_sitter_c as tsc
from tree_sitter import Language, Parser

C_LANGUAGE = Language(tsc.language())

from tree_sitter import Language, Parser


class Func(TypedDict):
    name: str
    start_line: int
    end_line: int


class File(object):

    def __init__(self, content: str) -> None:
        if content is None:
            raise ValueError("Content cannot be None")

        self.content = content
        self.parser = Parser(C_LANGUAGE)
        self.tree = self.parser.parse(bytes(content, "utf8"))
        self.root_node = self.tree.root_node

        self._funcs: list[Func] | None = None
        self._line_func_map: list[Func | None] | None = None

    @property
    def funcs(self) -> list[Func]:
        if self._funcs is None:
            self._funcs = self.find_funcs()
        return self._funcs

    @property
    def line_func_map(self) -> list[Func | None]:
        if self._line_func_map is None:
            self._line_func_map = self.make_line_func_map()
        return self._line_func_map

    def find_funcs(self, node=None) -> list[Func]:
        """
        Find all function definitions recursively and return a list of function information.
        """
        if node is None:
            node = self.root_node
        functions = []
        if node.type == "function_definition":
            function_declarator = node.child_by_field_name("declarator")
            if function_declarator:
                function_name_node = function_declarator.child_by_field_name(
                    "declarator"
                )
                if function_name_node:
                    function_name = function_name_node.text.decode("utf8")
                    start_line = node.start_point[0] + 1
                    end_line = node.end_point[0] + 1
                    functions.append(
                        Func(
                            name=function_name, start_line=start_line, end_line=end_line
                        )
                    )
        for child in node.children:
            functions.extend(self.find_funcs(child))
        return functions

    def make_line_func_map(self) -> list[Func | None]:

        total_lines = len(self.content.splitlines())
        line_map = [None] * total_lines
        for func in self.funcs:
            for i in range(func["start_line"] - 1, func["end_line"]):
                if 0 <= i < total_lines:
                    line_map[i] = func

        return line_map

    def locate_line(self, line: int) -> Func | None:
        """
        Locate the function that contains the specified line number.
        """

        if 0 <= line - 1 < len(self.line_func_map):
            return self.line_func_map[line - 1]
        return None
