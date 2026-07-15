"""Flag branch bodies proved impossible by earlier same-value returns.

Thin engine-backed rule: detection lives in ``unreachable_branch_detector``.
Grandfathered rows use ``python/unreachable-branch-baseline.json`` with the
occurrence codec and legacy ``normalized_condition`` field name.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

from larch.core import proc
from larch.lint.engine import (
    EXIT_ERROR,
    Finding as EngineFinding,
    LintRule,
    SourceFile,
    run_rule,
)
from larch.lint.unreachable_branch_detector import (  # pylint: disable=unused-import  # re-export
    SUPPRESSION,
    Finding,  # type: ignore[reportUnusedImport]  # re-exported for equivalence/detector tests
    is_production_source_path,
    iter_source_files,  # type: ignore[reportUnusedImport]  # re-exported for equivalence/detector tests
    scan_file,  # type: ignore[reportUnusedImport]  # re-exported for equivalence/detector tests
    scan_module,
)

RULE_ID = SUPPRESSION
BASELINE_FILENAME = "unreachable-branch-baseline.json"
PATHSPECS = ("python/larch/*.py", "python/larch/**/*.py")


def detect(source: SourceFile) -> list[EngineFinding]:
    """Adapt detector hits into engine findings with occurrence identity."""
    if not source.is_python:
        return []
    tree = source.python_ast
    if not isinstance(tree, ast.Module):
        return []
    if source.path.startswith("python/"):
        normalized_file = source.path[len("python/") :]
    else:
        normalized_file = source.path
    hits = scan_module(tree, normalized_file=normalized_file, source=source.text)
    return [
        EngineFinding(
            path=source.path,
            line=hit.lineno,
            rule_id=RULE_ID,
            message=(
                f"unreachable branch occurrence {hit.occurrence} "
                f"cond={hit.normalized_condition}"
            ),
            qualified_symbol=hit.qualified_symbol,
            pattern_name=hit.normalized_condition,
            occurrence=hit.occurrence,
        )
        for hit in hits
    ]


RULE = LintRule(
    rule_id=RULE_ID,
    description=(
        "Flag branch bodies proved impossible by earlier same-value returns"
    ),
    detect=detect,
    syntax_policy="raise",
    suppression_token=SUPPRESSION,
    allow_inline_suppression=False,
    pathspecs=PATHSPECS,
    source_filter=is_production_source_path,
    occurrence_baseline=True,
    require_baseline=True,
    stale_baseline_on_clean_scan=False,
    occurrence_pattern_field="normalized_condition",
)


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(
        prog="cli.py lint unreachable-branch",
        description=__doc__,
    )
    _ = parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[3]),
        help="Repository root (default: checkout containing this module).",
    )
    _ = parser.add_argument(
        "--write",
        action="store_true",
        help=f"Regenerate {BASELINE_FILENAME} from the live AST scan.",
    )
    _ = parser.add_argument(
        "--initial-reason",
        help="Reason for live findings that have no preserved baseline reason.",
    )
    try:
        return parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None


def main(argv: list[str] | None = None) -> int:
    """CLI entry registered as ``python3 python/cli.py lint unreachable-branch``."""
    parsed = _parse_args(argv if argv is not None else sys.argv[1:])
    if parsed is None:
        return EXIT_ERROR
    root = Path(str(parsed.root)).resolve()
    baseline_path = root / "python" / BASELINE_FILENAME
    initial_reason = parsed.initial_reason
    if initial_reason is not None and not str(initial_reason).strip():
        print(
            "lint-unreachable-branch: --initial-reason must be non-empty",
            file=sys.stderr,
        )
        return EXIT_ERROR
    return run_rule(
        RULE,
        root,
        proc.ProcRunner(),
        paths=None,
        baseline_path=baseline_path,
        write_baseline=bool(parsed.write),
        initial_reason=None if initial_reason is None else str(initial_reason),
        strict_stale=not bool(parsed.write),
    )


if __name__ == "__main__":
    raise SystemExit(main())
