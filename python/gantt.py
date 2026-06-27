"""Backward-compat shim; canonical location is larch.rendering.gantt."""
import sys as _sys
import larch.rendering.gantt as _m
_sys.modules[__name__] = _m
