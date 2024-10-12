import json
import re
from collections import defaultdict


# 第一步：提取数据并生成 filtered_config.json
def extract_data():
    # 读取现有的 JSON 文件
    with open("example_extra_config.json", "r", encoding="utf-8") as file:
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
            new_data.append(
                {
                    "kind": kind,
                    "file": file_name,
                    "message": message,
                    "symbol": symbols if symbols else None,
                }
            )

    # 将新的数据保存到新的 JSON 文件中
    with open("filtered_config.json", "w", encoding="utf-8") as file:
        json.dump(new_data, file, ensure_ascii=False, indent=4)


# 第二步：合并 symbol 列表并生成 merged_config.json
def merge_symbols():
    # 读取现有的 JSON 文件
    with open("filtered_config.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    # 使用 defaultdict 合并 symbol 列表
    merged_data = defaultdict(set)
    for item in data:
        file_name = item.get("file")
        symbols = item.get("symbol", [])
        if file_name:
            if symbols is None:
                symbols = []
            merged_data[file_name].update(symbols)

    # 将合并后的数据转换为字典格式
    result = {file: list(symbols) for file, symbols in merged_data.items()}

    # 将新的数据保存到新的 JSON 文件中
    with open("merged_config.json", "w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=4)


# 执行步骤
extract_data()
merge_symbols()
