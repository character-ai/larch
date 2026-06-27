"""Backward-compat shim; canonical location is larch.release.release_prepare."""
import sys as _sys
import larch.release.release_prepare as _m
_sys.modules[__name__] = _m
