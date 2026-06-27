"""Backward-compat shim; canonical location is larch.review.plan_review_tally."""
import sys as _sys
import larch.review.plan_review_tally as _m
_sys.modules[__name__] = _m
