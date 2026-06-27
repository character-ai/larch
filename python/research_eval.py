"""Backward-compat shim; canonical location is larch.research.research_eval."""
import sys as _sys
import larch.research.research_eval as _m
_sys.modules[__name__] = _m
