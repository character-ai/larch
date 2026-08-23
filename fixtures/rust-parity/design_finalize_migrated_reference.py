"""Frozen Python reference for migrated design finalization verbs (#8586)."""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

from larch.core import repo_roots as _repo_roots
from design_pause_dispatch_stub import install as _install_design_package

FROZEN = Path(__file__).resolve().parent / "design_finalize_frozen"
_ORIGINAL_ENTRYPOINT = _repo_roots.larch_entrypoint


def _entrypoint(root: Path | None = None) -> Path:
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


_core = _load("larch.design.design_core", FROZEN / "design_core.py")
_step5c = _load("larch.design.design_step5c", FROZEN / "design_step5c.py")
_step6 = _load("larch.design.design_step6", FROZEN / "design_step6.py")

DISPATCH = {
    "compose-plan-md": _step5c.compose_plan_md_main,
    "step2b5": _step5c.step2b5_main,
    "step5c": _step5c.step5c_main,
    "step6": _step6.step6_main,
    "step6-cleanup": _step6.step6_cleanup_main,
    "step6-prelude": _step6.step6_prelude_main,
}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in DISPATCH:
        print("design_finalize_migrated_reference: missing or unknown verb", file=sys.stderr)
        return 2
    return int(DISPATCH[args[0]](args[1:]))


if __name__ == "__main__":
    raise SystemExit(main())
