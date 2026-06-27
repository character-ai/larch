"""Backward-compat shim; canonical location is larch.lint.lint_subprocess_via_runner."""
import sys as _sys
import larch.lint.lint_subprocess_via_runner as _m
_sys.modules[__name__] = _m
