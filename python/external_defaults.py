"""Backward-compat shim; canonical location is larch.core.external_defaults."""
import sys as _sys
import larch.core.external_defaults as _m
_sys.modules[__name__] = _m
