"""Backward-compat shim; canonical location is larch.design.design_publish."""
import sys as _sys
import larch.design.design_publish as _m
_sys.modules[__name__] = _m
