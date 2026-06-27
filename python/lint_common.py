"""Backward-compat shim; canonical location is larch.lint.lint_common."""
import sys as _sys
import larch.lint.lint_common as _m
_sys.modules[__name__] = _m
