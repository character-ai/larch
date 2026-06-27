"""Backward-compat shim; canonical location is larch.implement.phantom."""
import sys as _sys
import larch.implement.phantom as _m
_sys.modules[__name__] = _m
