"""Backward-compat shim; canonical location is larch.report.gc_run_logs."""
import sys as _sys
import larch.report.gc_run_logs as _m
_sys.modules[__name__] = _m
