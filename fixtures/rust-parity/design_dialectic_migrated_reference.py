"""Frozen Python reference for the four dialectic candidate commands (#8584)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

FROZEN = Path(__file__).resolve().parent / "design_dialectic_frozen" / "design_dialectic.py"


def _load():
    name = "larch.design._frozen_design_dialectic"
    spec = importlib.util.spec_from_file_location(name, FROZEN)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load frozen module {FROZEN}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_dialectic = _load()

DISPATCH = {
    "dialectic-clear-stale": _dialectic.clear_stale_main,
    "dialectic-promote-candidates": _dialectic.promote_candidates_main,
    "dialectic-validate-candidates": _dialectic.validate_candidates_main,
    "dialectic-write-candidates": _dialectic.write_candidates_main,
}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("design_dialectic_migrated_reference: missing verb", file=sys.stderr)
        return 2
    verb, rest = args[0], args[1:]
    handler = DISPATCH.get(verb)
    if handler is None:
        print(f"design_dialectic_migrated_reference: unknown verb {verb}", file=sys.stderr)
        return 2
    return int(handler(rest))


if __name__ == "__main__":
    raise SystemExit(main())
