"""Test-only bridge from frozen Python fixtures to the Rust pause owner.

The migrated Step 0 and plan-quality references remain byte-frozen and import
the pause module that existed when those snapshots were taken. Production no
longer ships that module after #8589, so their harnesses inject this dispatcher
instead of retaining a second pause implementation.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType

from larch.core.repo_roots import larch_entrypoint


def _run(verb: str, argv: Sequence[str]) -> int:
    root = Path(__file__).resolve().parents[2]
    executable = os.environ.get("LARCH_BINARY") or str(larch_entrypoint(root))
    return subprocess.run(
        [executable, "design", verb, *argv],
        check=False,
    ).returncode


def install() -> None:
    """Install the two-function historical import surface for frozen tests."""

    def pause_save_main(argv: Sequence[str]) -> int:
        return _run("pause-save", argv)

    def pause_load_main(argv: Sequence[str]) -> int:
        return _run("pause-load", argv)

    module = ModuleType("larch.design.design_pause")
    module.pause_save_main = pause_save_main
    module.pause_load_main = pause_load_main
    sys.modules[module.__name__] = module

    import larch.design as design_package  # noqa: PLC0415 - install after package initialization

    design_package.design_pause = module
