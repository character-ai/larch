"""Backward-compat shim; canonical location is larch.lint.migration_lint."""
import sys as _sys
import larch.lint.migration_lint as _m
_sys.modules[__name__] = _m
