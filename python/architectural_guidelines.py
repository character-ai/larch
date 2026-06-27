"""Backward-compat shim; canonical location is larch.core.architectural_guidelines."""
import sys as _sys
import larch.core.architectural_guidelines as _m
_sys.modules[__name__] = _m
