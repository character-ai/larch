"""Backward-compat shim; canonical location is larch.rendering.render_chart."""
import sys as _sys
import larch.rendering.render_chart as _m
_sys.modules[__name__] = _m
