"""Load retired issue helpers for frozen Python parity references."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def install_issue_support() -> None:
    """Install frozen issue helpers under their historical module names."""
    import larch.issue  # noqa: PLC0415 - attach after the package exists

    frozen_root = Path(__file__).resolve().with_name("issue_support_frozen")
    for leaf in ("file_oos", "oos_priority", "title_match"):
        name = f"larch.issue.{leaf}"
        module = sys.modules.get(name)
        if module is None:
            path = frozen_root / f"{leaf}.py"
            spec = importlib.util.spec_from_file_location(name, path)
            if spec is None or spec.loader is None:
                raise RuntimeError(f"cannot load frozen module {path}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
        setattr(larch.issue, leaf, module)
