"""Backward-compat shim; canonical location is larch.release.promote_release."""
import sys as _sys
import larch.release.promote_release as _m
_sys.modules[__name__] = _m
