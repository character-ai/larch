"""Backward-compat shim; canonical location is larch.lint.pylint_sharding."""
import sys as _sys
import larch.lint.pylint_sharding as _m
_sys.modules[__name__] = _m
