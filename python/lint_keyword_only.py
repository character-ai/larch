"""Backward-compat shim; canonical location is larch.lint.lint_keyword_only."""
import sys as _sys
import larch.lint.lint_keyword_only as _m
_sys.modules[__name__] = _m
