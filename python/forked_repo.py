"""Backward-compat shim; canonical location is larch.core.forked_repo."""
import sys as _sys
import larch.core.forked_repo as _m
_sys.modules[__name__] = _m
