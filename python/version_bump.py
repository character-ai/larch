"""Backward-compat shim; canonical location is larch.release.version_bump."""
import sys as _sys
import larch.release.version_bump as _m
_sys.modules[__name__] = _m
