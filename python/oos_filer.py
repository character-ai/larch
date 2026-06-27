"""Backward-compat shim; canonical location is larch.issue.oos_filer."""
import sys as _sys
import larch.issue.oos_filer as _m
_sys.modules[__name__] = _m
