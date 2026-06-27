"""Backward-compat shim; canonical location is larch.rendering.render_session_transcript."""
import sys as _sys
import larch.rendering.render_session_transcript as _m
_sys.modules[__name__] = _m
