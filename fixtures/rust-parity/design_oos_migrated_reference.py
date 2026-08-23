"""Frozen pre-#8590 reference dispatcher for design OOS parity tests.

Production no longer ships ``larch.design.design_oos``. The adjacent frozen
module is its final Python implementation. Only runtime-entrypoint references
are adapted: subcommands use the harness-provided Rust binary because
``scripts/larch.sh`` intentionally refuses an unbuilt checkout, and warning
records name that verified entrypoint instead of the retired Python one.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from design_pause_dispatch_stub import (
    install_shared_retired_dependencies as _install_retired_dependencies,
)

_install_retired_dependencies()


def _load_reference() -> Any:
    path = Path(__file__).with_name("design_oos_frozen.py")
    spec = importlib.util.spec_from_file_location("design_oos_frozen", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load frozen module {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REFERENCE = _load_reference()


def _run_larch(argv: list[str]) -> subprocess.CompletedProcess[str]:
    binary = os.environ["LARCH_BINARY"]
    return subprocess.run(
        [binary, *argv[1:]],
        capture_output=True,
        text=True,
        check=False,
        env=os.environ,
    )


REFERENCE._run_larch = _run_larch
_append_warning_log = REFERENCE._append_warning_log


def _append_migrated_warning(**kwargs: Any) -> Any:
    tool = kwargs.get("tool", "")
    if tool.startswith("python/cli.py design file-oos-"):
        kwargs["tool"] = tool.replace("python/cli.py", "scripts/larch.sh", 1)
    return _append_warning_log(**kwargs)


REFERENCE._append_warning_log = _append_migrated_warning


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("design_oos_migrated_reference: missing verb", file=sys.stderr)
        return 2
    verb, rest = args[0], args[1:]
    if verb == "file-oos-prepare":
        return int(REFERENCE.file_oos_prepare_main(rest))
    if verb == "file-oos-annotate":
        return int(REFERENCE.file_oos_annotate_main(rest))
    print(f"design_oos_migrated_reference: unknown verb {verb}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
