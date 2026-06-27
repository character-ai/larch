"""Backward-compat shim; canonical location is larch.core.verify_skill."""
import sys as _sys
import larch.core.verify_skill as _m
_sys.modules[__name__] = _m
