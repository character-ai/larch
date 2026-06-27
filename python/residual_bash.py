"""Backward-compat shim; canonical location is larch.core.residual_bash."""
import sys as _sys
import larch.core.residual_bash as _m
_sys.modules[__name__] = _m
