"""Frozen Python reference for `/implement` Steps 16 and 17 (#8791).

The loaded module is the retired production owner with only its module
docstring changed. The parity suite supplies an isolated verified-bootstrap
stub, so every case exercises the old command boundary and wire side effects
without network access.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Callable


def _load() -> ModuleType:
    path = Path(__file__).resolve().parent / "implement_closeout_frozen" / "closeout.py"
    spec = importlib.util.spec_from_file_location("larch.state.closeout_frozen", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load frozen module {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_CLOSEOUT = _load()
_DISPATCH: dict[str, Callable[[list[str] | None], int]] = {
    "step-16": _CLOSEOUT.step_16_main,
    "step-16-16a": _CLOSEOUT.step_16_16a_main,
    "step-16-17": _CLOSEOUT.step_16_17_main,
    "step-17": _CLOSEOUT.step_17_main,
}


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments:
        print("implement_closeout_reference: missing verb", file=sys.stderr)
        return 2
    verb, rest = arguments[0], arguments[1:]
    handler = _DISPATCH.get(verb)
    if handler is None:
        print(f"implement_closeout_reference: unknown verb {verb}", file=sys.stderr)
        return 2
    return int(handler(rest))


if __name__ == "__main__":
    raise SystemExit(main())
