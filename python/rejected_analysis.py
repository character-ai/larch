"""Backward-compat shim; canonical location is larch.issue.rejected_analysis."""
import sys as _sys
import larch.issue.rejected_analysis as _m
_sys.modules[__name__] = _m
