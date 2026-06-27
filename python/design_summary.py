"""Backward-compat shim; canonical location is larch.design.design_summary."""
import sys as _sys
import larch.design.design_summary as _m
_sys.modules[__name__] = _m
