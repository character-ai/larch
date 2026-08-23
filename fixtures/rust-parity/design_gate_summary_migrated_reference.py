"""Frozen Python reference for migrated `/design` render verbs (#8581).

Loads the pre-cutover modules from ``design_gate_summary_frozen/`` so Rust can be
black-box parity tested after production Python registration removal, mirroring
``design_terminal_migrated_reference.py``. The frozen copies are byte-identical
snapshots of the retired ``python/larch/design/design_gate_render.py`` and
``python/larch/design/design_summary.py``.

The frozen ``design_summary`` copy imports common package modules directly. The
retired ``larch.design.design_core`` dependency is preloaded from the existing
finalization fixture under its original module name. One documented harness
adjustment remains:

1. Subprocesses that ran through ``repo_roots.larch_entrypoint`` (``timing report``,
   ``run-log`` writes, the ``design failure-report`` gate, and the
   ``tracking-issue upsert-summary`` neighbor) prefer the harness-provided larch
   binary (``LARCH_BINARY`` env, exported by the parity test as
   ``CARGO_BIN_EXE_larch``) because ``scripts/larch.sh`` refuses to run from an
   unbuilt git checkout. The preference is installed by monkeypatching
   ``repo_roots.larch_entrypoint`` before the frozen module binds that name.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

FROZEN = Path(__file__).resolve().parent / "design_gate_summary_frozen"
CORE_FROZEN = Path(__file__).resolve().parent / "design_finalize_frozen" / "design_core.py"

from larch.core import repo_roots as _repo_roots  # noqa: E402
from design_pause_dispatch_stub import install as _install_design_package  # noqa: E402

_ORIGINAL_ENTRYPOINT = _repo_roots.larch_entrypoint


def _entrypoint(root: Path) -> Path:
    """Documented adjustment 1: prefer the harness-provided larch binary."""
    override = os.environ.get("LARCH_BINARY")
    return Path(override) if override else _ORIGINAL_ENTRYPOINT(root)


# Patch before the frozen modules run their `from ... import larch_entrypoint`
# so the by-name binding resolves to the harness-preferring entrypoint.
_repo_roots.larch_entrypoint = _entrypoint  # type: ignore[assignment]
_install_design_package()


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load frozen module {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_core = _load("larch.design.design_core", CORE_FROZEN)
_gate = _load("larch.design._frozen_design_gate_render", FROZEN / "design_gate_render.py")
_summary = _load("larch.design._frozen_design_summary", FROZEN / "design_summary.py")

DISPATCH = {
    "render-gate": _gate.render_gate_main,
    "render-final-summary": _summary.render_final_summary_main,
}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    # The retired verbs ran as `python cli.py design <verb> ...`, so their
    # `argparse` prog resolved to `cli.py`; the Rust owner reproduces that exact
    # usage/error prefix, so the frozen reference must match it here.
    sys.argv[0] = "cli.py"
    if not args:
        print("design_gate_summary_migrated_reference: missing verb", file=sys.stderr)
        return 2
    verb, rest = args[0], args[1:]
    handler = DISPATCH.get(verb)
    if handler is None:
        print(f"design_gate_summary_migrated_reference: unknown verb {verb}", file=sys.stderr)
        return 2
    return int(handler(rest))


if __name__ == "__main__":
    raise SystemExit(main())
