"""Backward-compat shim; canonical location is larch.calibration.calibration_replay."""
import sys as _sys
import larch.calibration.calibration_replay as _m
_sys.modules[__name__] = _m
