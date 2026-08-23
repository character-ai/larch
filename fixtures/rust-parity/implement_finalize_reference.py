"""Black-box entrypoint for the frozen pre-#8793 finalize owner."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Callable


def _load() -> ModuleType:
    path = Path(__file__).with_name("implement_finalize_frozen.py")
    spec = importlib.util.spec_from_file_location(
        "larch.state.implement_finalize_frozen", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load frozen module {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_FINALIZE = _load()
_DISPATCH: dict[str, Callable[[list[str] | None], int]] = {
    "cleanup": _FINALIZE.cleanup_main,
    "postbump": _FINALIZE.implement_finalize_postbump_main,
    "postmerge": _FINALIZE.implement_finalize_postmerge_main,
    "teardown": _FINALIZE.implement_finalize_teardown_main,
}


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments[0] not in _DISPATCH:
        print("implement_finalize_reference: missing or unknown verb", file=sys.stderr)
        return 2
    return int(_DISPATCH[arguments[0]](arguments[1:]))


if __name__ == "__main__":
    raise SystemExit(main())
