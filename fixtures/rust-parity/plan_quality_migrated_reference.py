"""Frozen Python reference for migrated plan validation/auto-fix verbs (#8576).

Loads the pre-cutover modules from ``plan_quality_frozen/`` so Rust can be
black-box parity tested after production Python registration removal.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

FROZEN = Path(__file__).resolve().parent / "plan_quality_frozen"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load frozen module {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Commands module must load first; full module imports it as `_plan_quality_commands`.
_commands = _load("_plan_quality_commands", FROZEN / "_plan_quality_commands.py")
_full = _load("plan_quality_full", FROZEN / "plan_quality_full.py")

DISPATCH = {
    "parse-commands": _commands.parse_plan_commands_main,
    "validate-commands": _commands.validate_plan_commands_main,
    "validate": _commands.validate_plan_main,
    "check-size": _full.check_plan_size_main,
    "set-oversize-override": _full.set_oversize_override_main,
    "revise-waterfall": _full.revise_plan_with_waterfall_main,
    "auto-fix-commands": _full.auto_fix_plan_commands_main,
    "validator-autofix": _full.validator_autofix_main,
    "optional-trailers": _full.optional_trailers_main,
    "compose-goals-test": _full.compose_plan_goals_test_main,
}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("plan_quality_migrated_reference: missing verb", file=sys.stderr)
        return 2
    verb, rest = args[0], args[1:]
    handler = DISPATCH.get(verb)
    if handler is None:
        print(f"plan_quality_migrated_reference: unknown verb {verb}", file=sys.stderr)
        return 2
    return int(handler(rest))


if __name__ == "__main__":
    raise SystemExit(main())
