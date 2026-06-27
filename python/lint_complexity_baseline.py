"""Backward-compat shim; canonical location is larch.lint.lint_complexity_baseline."""
import sys as _sys
import larch.lint.lint_complexity_baseline as _m
_sys.modules[__name__] = _m
