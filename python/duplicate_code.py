"""Backward-compat shim; canonical location is larch.lint.duplicate_code."""
import sys as _sys
import larch.lint.duplicate_code as _m
_sys.modules[__name__] = _m
