"""Backward-compat shim; canonical location is larch.core.verify_main."""
import sys as _sys
import larch.core.verify_main as _m
_sys.modules[__name__] = _m
