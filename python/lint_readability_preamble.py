"""Backward-compat shim; canonical location is larch.lint.lint_readability_preamble."""
import sys as _sys
import larch.lint.lint_readability_preamble as _m
_sys.modules[__name__] = _m
