"""Frozen Python reference for the migrated `/voter-calibration` analyzer (#8672).

Loads the retired analyzer and its four retired `larch.issue` support modules
from ``voter_calibration_frozen/`` so Rust can be black-box parity tested after
production Python removal. The frozen copies stay verbatim: this loader
pre-registers them under their historical ``larch.issue`` module names, so the
frozen inter-module imports resolve package-locally while surviving imports
(``larch.calibration.voting``, ``larch.report.run_log_corpus``, ``larch.core``,
``larch.git.gh``) still resolve from the repository ``python/`` tree.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

FROZEN = Path(__file__).resolve().parent / "voter_calibration_frozen"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load frozen module {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Dependency order: _util has no frozen imports; _report and _oos import _util;
# _ground_truth imports all three; the analyzer imports _ground_truth, _oos,
# and _util through the pre-registered names.
_load("larch.issue._util", FROZEN / "_util.py")
_load("larch.issue._report", FROZEN / "_report.py")
_load("larch.issue._oos", FROZEN / "_oos.py")
_load("larch.issue._ground_truth", FROZEN / "_ground_truth.py")
_full = _load("voter_calibration_full", FROZEN / "voter_calibration_full.py")


if __name__ == "__main__":
    raise SystemExit(_full.main(sys.argv[1:]))
