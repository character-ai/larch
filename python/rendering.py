"""Backward-compat shim; canonical location is larch.rendering.rendering."""
import sys as _sys
import larch.rendering.rendering as _m
_sys.modules[__name__] = _m
