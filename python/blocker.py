"""Backward-compat shim; canonical location is larch.issue.blocker."""
import sys as _sys
import larch.issue.blocker as _m
_sys.modules[__name__] = _m
