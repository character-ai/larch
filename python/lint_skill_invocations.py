"""Backward-compat shim; canonical location is larch.lint.lint_skill_invocations."""
import sys as _sys
import larch.lint.lint_skill_invocations as _m
_sys.modules[__name__] = _m
