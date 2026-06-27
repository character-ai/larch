"""Backward-compat shim; canonical location is larch.release.release_finish."""
import sys as _sys
import larch.release.release_finish as _m
_sys.modules[__name__] = _m
