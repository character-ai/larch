"""Frozen Python reference for migrated `/design` step1 verbs (#8579).

Loads the pre-cutover modules from ``design_step1_frozen/`` so Rust can be
black-box parity tested after production Python registration removal, mirroring
``design_step0_migrated_reference.py``. The two frozen modules are
byte-identical copies of the retired
``python/larch/design/{design_step1,design_step_log}.py``.

Unlike the Step 0 reference, these frozen copies import the surviving
``larch.design.design_core``/``larch.core.repo_roots``/``larch.io`` package
modules directly, so no ``sys.modules`` cross-import shim is needed. One
documented harness adjustment remains:

1. Subprocesses that ran through ``repo_roots.larch_entrypoint`` (plan-review
   emit/tally/finalize, plan validate, agent collect-results, dirty-tree
   checkpoint, timing mark, run-log write/append-failure) prefer the
   harness-provided larch binary (``LARCH_BINARY`` env, exported by the parity
   test as ``CARGO_BIN_EXE_larch``) because ``scripts/larch.sh`` refuses to run
   from an unbuilt git checkout. The preference is installed by monkeypatching
   ``repo_roots.larch_entrypoint`` before the frozen modules bind that name.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

FROZEN = Path(__file__).resolve().parent / "design_step1_frozen"

from larch.core import repo_roots as _repo_roots  # noqa: E402

_ORIGINAL_ENTRYPOINT = _repo_roots.larch_entrypoint


def _entrypoint(root: Path) -> Path:
    """Documented adjustment 1: prefer the harness-provided larch binary.

    Returns a ``Path`` (not ``str``) because the frozen ``design_step_log``
    calls ``larch_entrypoint(plugin_root).is_file()`` directly, while the
    ``design_step1`` call sites wrap the result in ``str(...)``.
    """
    override = os.environ.get("LARCH_BINARY")
    return Path(override) if override else _ORIGINAL_ENTRYPOINT(root)


# Patch before the frozen modules run their `from ... import larch_entrypoint`
# so those by-name bindings resolve to the harness-preferring entrypoint.
_repo_roots.larch_entrypoint = _entrypoint  # type: ignore[assignment]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load frozen module {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_step1 = _load("larch.design._frozen_design_step1", FROZEN / "design_step1.py")
_step_log = _load("larch.design._frozen_design_step_log", FROZEN / "design_step_log.py")

DISPATCH = {
    "driver": _step1.driver_main,
    "step1d5": _step1.step1d5_main,
    "step1d7": _step1.step1d7_main,
    "step1e-reentry": _step1.step1e_reentry_main,
    "step1-log": _step_log.step1_log_main,
}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("design_step1_migrated_reference: missing verb", file=sys.stderr)
        return 2
    verb, rest = args[0], args[1:]
    handler = DISPATCH.get(verb)
    if handler is None:
        print(f"design_step1_migrated_reference: unknown verb {verb}", file=sys.stderr)
        return 2
    return int(handler(rest))


if __name__ == "__main__":
    raise SystemExit(main())
