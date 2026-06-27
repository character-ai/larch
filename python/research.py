"""Backward-compat shim; canonical location is larch.research.research."""
import sys as _sys
import larch.research.research as _m
_sys.modules[__name__] = _m
