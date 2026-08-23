"""Argparse-based subcommand dispatcher for larch Python runtime.

Canonical location; python/cli.py is the entry-point shim.
Direct-call convention: consumers invoke
    python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" <domain> <verb> [args...]
No .sh shim files, ever. See docs/python-migration.md for the migration playbook.
"""

from __future__ import annotations

import argparse
import importlib
import os
import sys

_REGISTRY: dict[tuple[str, str], tuple[str, str, bool]] = {
    ("complete-umbrella", "bootstrap"): (
        "larch.complete_umbrella",
        "bootstrap_main",
        True,
    ),
    ("plan-review", "write-loop-identity"): ("larch.core.process_identity", "write_loop_identity_main", False),
    ("plan-review", "await-loop-identity"): ("larch.core.process_identity", "await_loop_identity_main", False),
    ("plan-review", "teardown-loop-identity"): ("larch.core.process_identity", "teardown_loop_identity_main", False),
    ("render", "voter"): ("larch.rendering.rendering", "render_voter_main", False),
    ("render", "plan-review"): ("larch.rendering.rendering", "render_plan_review_main", False),
    ("render", "scope-anchor"): ("larch.rendering.rendering", "render_scope_anchor_main", False),
    ("scope-anchor", "relay-allowed"): ("larch.rendering.rendering", "scope_anchor_relay_allowed_main", False),
    ("scope-anchor", "validate"): ("larch.rendering.rendering", "scope_anchor_validate_main", False),
    ("scope-anchor", "retally-handoff"): ("larch.rendering.rendering", "scope_anchor_retally_handoff_main", False),
    ("scope-anchor", "design-handoff"): ("larch.rendering.rendering", "scope_anchor_design_handoff_main", False),
    ("mermaid", "sanitize"): ("larch.rendering.rendering", "mermaid_sanitize_main", False),
    ("diagrams", "upsert"): ("larch.rendering.rendering", "diagrams_upsert_main", False),
    ("diagram", "code-flow"): ("larch.git.pr_body", "generate_code_flow_diagram_main", True),
    ("render", "run-summary"): ("larch.git.pr_body", "render_run_summary_main", True),
    ("oos", "serialize"): ("larch.issue.oos", "oos_serialize_main", False),
    ("oos", "normalize-header"): ("larch.issue.oos", "oos_normalize_header_main", False),
}

# Compatibility view: keys whose registry row has machine_stdout=True.
# Derived from _REGISTRY; do not hand-maintain.
_MACHINE_STDOUT_KEYS: frozenset[tuple[str, str]] = frozenset(
    key for key, (_module, _func, machine_stdout) in _REGISTRY.items() if machine_stdout
)

def _version_supported(version_info: object) -> bool:
    return tuple(version_info) >= (3, 11)  # type: ignore[arg-type]


def _unsupported_version_exit(args: list[str]) -> int:
    _ = args
    print(
        "ERROR: larch cli.py requires Python 3.11 or newer",
        file=sys.stderr,
    )
    return 2


def _build_help_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="larch Python runtime dispatcher",
        add_help=True,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    domains: dict[str, list[str]] = {}
    for domain, verb in _REGISTRY:
        domains.setdefault(domain, []).append(verb)
    lines = ["Available subcommands:"]
    lines.extend(
        f"  {domain} {verb}" for domain in sorted(domains) for verb in sorted(domains[domain])
    )
    parser.epilog = "\n".join(lines)
    return parser


def _run_subcommand(module_name: str, func_name: str, rest_argv: list[str]) -> int:
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        print(f"ERROR: failed to import module {module_name!r}: {exc}", file=sys.stderr)
        return 2

    target_main = getattr(module, func_name, None)
    if target_main is None:
        print(
            f"ERROR: module {module_name!r} has no function {func_name!r}",
            file=sys.stderr,
        )
        return 2

    return int(target_main(rest_argv))


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]

    if not _version_supported(sys.version_info):
        return _unsupported_version_exit(args)

    if not args or args[0] in {"-h", "--help"}:
        _build_help_parser().print_help()
        return 0

    domain = args[0]
    if len(args) < 2 or args[1].startswith("-"):  # noqa: PLR2004
        print(
            f"ERROR: missing verb for domain {domain!r}. "
            f"Usage: cli.py <domain> <verb> [args...]",
            file=sys.stderr,
        )
        return 2

    verb = args[1]
    key = (domain, verb)
    if key not in _REGISTRY:
        known = ", ".join(f"{d} {v}" for d, v in sorted(_REGISTRY))
        print(
            f"ERROR: unknown subcommand {domain!r} {verb!r}. "
            f"Known: {known}",
            file=sys.stderr,
        )
        return 2

    module_name, func_name, machine_stdout = _REGISTRY[key]
    rest_argv = args[2:]
    if machine_stdout:
        os.environ["LARCH_QUIET_DISABLE"] = "1"

    return _run_subcommand(module_name, func_name, rest_argv)
