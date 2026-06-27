"""Backward-compat shim; canonical location is larch.issue.issue_block."""
import sys as _sys
import larch.issue.issue_block as _m
_sys.modules[__name__] = _m
