"""Backward-compat shim; canonical location is larch.core.cleanup_skill."""
import sys as _sys
import larch.core.cleanup_skill as _m
_sys.modules[__name__] = _m
