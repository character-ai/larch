"""Frozen Python reference for migrated `/design` argv and router verbs (#8577).

Loads the pre-cutover modules from ``design_router_frozen/`` so Rust can be
black-box parity tested after production Python registration removal. The
frozen ``design_router.py`` carries two documented adjustments; see its
docstring.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from design_pause_dispatch_stub import (
    install_shared_retired_dependencies as _install_retired_dependencies,
)

_install_retired_dependencies()

FROZEN = Path(__file__).resolve().parent / "design_router_frozen"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load frozen module {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_argv = _load("design_argv_frozen", FROZEN / "design_argv.py")
_router = _load("design_router_frozen_module", FROZEN / "design_router.py")

DISPATCH = {
    "parse-flags": _argv.parse_flags_main,
    "route": _router.route_main,
    "init-runparams": _router.init_runparams_main,
}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("design_router_migrated_reference: missing verb", file=sys.stderr)
        return 2
    verb, rest = args[0], args[1:]
    handler = DISPATCH.get(verb)
    if handler is None:
        print(f"design_router_migrated_reference: unknown verb {verb}", file=sys.stderr)
        return 2
    return int(handler(rest))


if __name__ == "__main__":
    raise SystemExit(main())
