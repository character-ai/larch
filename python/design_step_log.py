"""Backward-compat shim; canonical location is larch.design.design_step_log."""
import sys as _sys
import larch.design.design_step_log as _m
_sys.modules[__name__] = _m
