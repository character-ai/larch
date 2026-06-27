"""Backward-compat shim; canonical location is larch.lint.lint_mermaid_fences."""
import sys as _sys
import larch.lint.lint_mermaid_fences as _m
_sys.modules[__name__] = _m
