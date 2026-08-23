"""Frozen Python reference for migrated settlement and Step 5b verbs (#8585).

The byte-identical pre-cutover owners live below ``design_settle_frozen/``.
The parity harness points their Rust child invocations at the built larch
binary through ``LARCH_BINARY``; this mirrors the sibling design migration
references and keeps the test offline in an unbuilt checkout.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

FROZEN = Path(__file__).resolve().parent / "design_settle_frozen"

from larch.core import repo_roots as _repo_roots  # noqa: E402
from design_pause_dispatch_stub import install as _install_design_package  # noqa: E402

_ORIGINAL_ENTRYPOINT = _repo_roots.larch_entrypoint


def _entrypoint(root: Path | None = None) -> Path:
    """Prefer the harness binary for Python-owner child commands."""
    override = os.environ.get("LARCH_BINARY")
    if override:
        return Path(override)
    return _ORIGINAL_ENTRYPOINT(root) if root is not None else _ORIGINAL_ENTRYPOINT()


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


_core = _load(
    "larch.design.design_core",
    FROZEN.parent / "design_finalize_frozen" / "design_core.py",
)
_settle = _load("larch.design._frozen_design_settle", FROZEN / "design_settle.py")
_oos = _load(
    "larch.design.design_oos",
    FROZEN.parent / "design_oos_frozen.py",
)
_step5c = _load(
    "larch.design.design_step5c",
    FROZEN.parent / "design_finalize_frozen" / "design_step5c.py",
)
_step5b = _load("larch.design._frozen_design_step5b", FROZEN / "design_step5b.py")

DISPATCH = {
    "step35-settle": _settle.step35_settle_main,
    "step5b-prepare": _step5b.step5b_prepare_main,
    "step5b-annotate": _step5b.step5b_annotate_main,
}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("design_settle_migrated_reference: missing verb", file=sys.stderr)
        return 2
    verb, rest = args[0], args[1:]
    handler = DISPATCH.get(verb)
    if handler is None:
        print(f"design_settle_migrated_reference: unknown verb {verb}", file=sys.stderr)
        return 2
    return int(handler(rest))


if __name__ == "__main__":
    raise SystemExit(main())
