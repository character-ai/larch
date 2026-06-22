import ast
import lint_keyword_only as lko

src = "def f(a, b, *, c=1): pass\n"
tree = ast.parse(src)
func = tree.body[0]
parsed_args = func.args
for node, name in [(func, "func"), (parsed_args, "args"), (parsed_args.args[0], "arg a")]:
    seg = ast.get_source_segment(src, node)
    print(name, "seg:", repr(seg))
