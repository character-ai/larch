"""Backward-compat shim; canonical location is larch.implement.preflight."""
import sys as _sys
import larch.implement.preflight as _m
_sys.modules[__name__] = _m
