"""Frozen Python reference for migrated `/design` Step 0 verbs (#8578).

Loads the pre-cutover modules from ``design_step0_frozen/`` so Rust can be
black-box parity tested after production Python registration removal, mirroring
``design_router_migrated_reference.py``. The three frozen modules are
byte-identical copies of the retired
``python/larch/design/{design_step0_env,design_step0,design_session}.py``.

Three documented harness adjustments live here rather than in the frozen copies,
keeping those copies byte-frozen (the third is described at its call site):

1. The frozen modules cross-import one another as ``larch.design.design_step0_env``
   etc. They are registered in ``sys.modules`` under their original dotted names
   before execution so those intra-package imports resolve to the frozen copies
   even after production removal. ``design_core`` continues to resolve to the
   surviving package module. ``design_terminal`` was retired in #8580, so its
   byte-frozen copy from ``design_terminal_frozen/`` is registered under
   ``larch.design.design_terminal``; the retired pause import resolves to a
   test-only Rust dispatcher.
2. Subprocesses that ran through ``repo_roots.larch_entrypoint`` (design
   parse-flags/route/init-runparams, session setup/write-design-env, run-log,
   agent, progress, token, timing) prefer the harness-provided larch binary
   (``LARCH_BINARY`` env, exported by the parity test as ``CARGO_BIN_EXE_larch``)
   because ``scripts/larch.sh`` refuses to run from an unbuilt git checkout. The
   preference is installed by monkeypatching ``repo_roots.larch_entrypoint``.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

FROZEN = Path(__file__).resolve().parent / "design_step0_frozen"
TERMINAL_FROZEN = Path(__file__).resolve().parent / "design_terminal_frozen"

# Documented adjustment 3: the harness runs both sides under `LANG=C`. On
# CPython, PEP 538 C-locale coercion injects `LC_CTYPE=UTF-8` into this
# interpreter's environment, and that leaks into the `bash -c 'printf %q'`
# child the frozen `_bash_percent_q` codec spawns, making bash emit a mixed
# raw-byte/octal `$'...'` string that is invalid UTF-8. The Rust owner spawns
# the same bash child directly under `LANG=C` with no `LC_CTYPE`, so it records
# clean octal escapes. Dropping the coerced `LC_CTYPE` here makes the frozen
# reference's bash child observe the identical `LANG=C` environment as the Rust
# side; it does not touch this interpreter's already-initialized stdio codec.
os.environ.pop("LC_CTYPE", None)

from larch.core import repo_roots as _repo_roots  # noqa: E402
from design_pause_dispatch_stub import install as _install_pause_stub  # noqa: E402

_ORIGINAL_ENTRYPOINT = _repo_roots.larch_entrypoint


def _entrypoint(root: Path) -> str:
    """Documented adjustment 2: prefer the harness-provided larch binary."""
    return os.environ.get("LARCH_BINARY") or str(_ORIGINAL_ENTRYPOINT(root))


_repo_roots.larch_entrypoint = _entrypoint  # type: ignore[assignment]
_install_pause_stub()


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load frozen module {path}")
    module = importlib.util.module_from_spec(spec)
    # Documented adjustment 1: register under the original dotted name before
    # execution so intra-package cross-imports resolve to the frozen copy.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# `design_terminal` was retired in #8580; register its byte-frozen copy under the
# original dotted name so the frozen step0 module's
# `from larch.design.design_terminal import ...` resolves to pre-cutover behavior.
_load("larch.design.design_terminal", TERMINAL_FROZEN / "design_terminal.py")
_env = _load("larch.design.design_step0_env", FROZEN / "design_step0_env.py")
_session = _load("larch.design.design_session", FROZEN / "design_session.py")
_step0 = _load("larch.design.design_step0", FROZEN / "design_step0.py")

DISPATCH = {
    "step0-parse": _env.step0_parse_main,
    "step0-session": _step0.step0_session_entry_main,
    "step0-route": _step0.step0_route_main,
    "step0-init": _step0.step0_init_main,
    "step0-clarify-hard-halt": _step0.step0_clarify_hard_halt_main,
    "step0-abort-cleanup": _step0.step0_abort_cleanup_main,
    "step0-ap-continue": _step0.step0_ap_continue_main,
    "step0c": _step0.step0c_main,
    "settle-next-action": _session.settle_next_action_main,
}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("design_step0_migrated_reference: missing verb", file=sys.stderr)
        return 2
    verb, rest = args[0], args[1:]
    handler = DISPATCH.get(verb)
    if handler is None:
        print(f"design_step0_migrated_reference: unknown verb {verb}", file=sys.stderr)
        return 2
    return int(handler(rest))


if __name__ == "__main__":
    raise SystemExit(main())
