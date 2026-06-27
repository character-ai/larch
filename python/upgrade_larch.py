"""Backward-compat shim; canonical location is larch.core.upgrade_larch."""
import sys as _sys
import larch.core.upgrade_larch as _m
_sys.modules[__name__] = _m
