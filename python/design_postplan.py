"""Backward-compat shim; canonical location is larch.design.design_postplan."""
import sys as _sys
import larch.design.design_postplan as _m
_sys.modules[__name__] = _m
