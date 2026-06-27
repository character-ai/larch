"""Backward-compat shim; canonical location is larch.core.alias_skill."""
import sys as _sys
import larch.core.alias_skill as _m
_sys.modules[__name__] = _m
