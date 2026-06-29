from __future__ import annotations

import ast

from larch.lint import lint_keyword_only as lko
def test_has_bare_star_separator_detects_trailing_bare_star_without_kwonly() -> None:
    src = "def f(a, b, *): pass\n"
    args = ast.arguments(
        posonlyargs=[],
        args=[ast.arg(arg="a"), ast.arg(arg="b")],
        vararg=None,
        kwonlyargs=[],
        kw_defaults=[],
        kwarg=None,
        defaults=[],
    )
    func = ast.FunctionDef(
        name="f",
        args=args,
        body=[],
        decorator_list=[],
        lineno=1,
        col_offset=0,
    )
    assert lko._has_bare_star_separator(args, src, func)  # type: ignore[reportPrivateUsage]
