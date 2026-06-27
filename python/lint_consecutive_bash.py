"""Backward-compat shim; canonical location is larch.lint.lint_consecutive_bash."""
import sys as _sys
import larch.lint.lint_consecutive_bash as _m
_sys.modules[__name__] = _m
