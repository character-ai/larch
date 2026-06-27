"""Backward-compat shim; canonical location is larch.review.compose_review."""
import sys as _sys
import larch.review.compose_review as _m
_sys.modules[__name__] = _m
