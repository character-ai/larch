"""Backward-compat shim; canonical location is larch.lint.lint_no_raw_stderr_after_quiet_init."""
import sys as _sys
import larch.lint.lint_no_raw_stderr_after_quiet_init as _m
_sys.modules[__name__] = _m
