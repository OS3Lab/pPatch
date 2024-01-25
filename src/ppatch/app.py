import pprint

import typer
import whatthepatch

app = typer.Typer()


@app.command()
def show(filename: str):
    content = ""
    with open(filename, mode="r", encoding="utf-8") as (f):
        content = f.read()

    diffes = whatthepatch.parse_patch(content)

    # for diff in diffes:
    #     if
    #     changes = diff.changes


@app.command()
def trace(filename: str):
    typer.echo(f"tracing patch {filename}")


# diff(
#     header=header(
#         index_path=None,
#         old_path="kernel/cgroup/cgroup-v1.c",
#         old_version="ee93b6e895874",
#         new_path="kernel/cgroup/cgroup-v1.c",
#         new_version="527917c0b30be",
#     ),
#     changes=[
#         Change(
#             old=912,
#             new=912,
#             line="\topt = fs_parse(fc, cgroup1_fs_parameters, param, &result);",
#             hunk=1,
#         ),
#         Change(old=913, new=913, line="\tif (opt == -ENOPARAM) {", hunk=1),
#         Change(
#             old=914,
#             new=914,
#             line='\t\tif (strcmp(param->key, "source") == 0) {',
#             hunk=1,
#         ),
#         Change(
#             old=None,
#             new=915,
#             line="\t\t\tif (param->type != fs_value_is_string)",
#             hunk=1,
#         ),
#         Change(
#             old=None,
#             new=916,
#             line='\t\t\t\treturn invalf(fc, "Non-string source");',
#             hunk=1,
#         ),
#         Change(old=915, new=917, line="\t\t\tif (fc->source)", hunk=1),
#         Change(
#             old=916,
#             new=918,
#             line='\t\t\t\treturn invalf(fc, "Multiple sources not supported");',
#             hunk=1,
#         ),
#         Change(old=917, new=919, line="\t\t\tfc->source = param->string;", hunk=1),
#     ],
#     text='diff --git a/kernel/cgroup/cgroup-v1.c b/kernel/cgroup/cgroup-v1.c\nindex ee93b6e895874..527917c0b30be 100644\n--- a/kernel/cgroup/cgroup-v1.c\n+++ b/kernel/cgroup/cgroup-v1.c\n@@ -912,6 +912,8 @@ int cgroup1_parse_param(struct fs_context *fc, struct fs_parameter *param)\n \topt = fs_parse(fc, cgroup1_fs_parameters, param, &result);\n \tif (opt == -ENOPARAM) {\n \t\tif (strcmp(param->key, "source") == 0) {\n+\t\t\tif (param->type != fs_value_is_string)\n+\t\t\t\treturn invalf(fc, "Non-string source");\n \t\t\tif (fc->source)\n \t\t\t\treturn invalf(fc, "Multiple sources not supported");\n \t\t\tfc->source = param->string;\n-- \ncgit \n\n',
# )
