"""Ban pylint skip-file and module-level duplicate-code disables in runtime modules.

Scans tracked Python files under ``python/larch/`` for:

- ``# pylint: skip-file``
- Module-level ``# pylint: disable=R0801`` / ``duplicate-code``

Uses ``larch.lint.engine.run_rule`` with a strict reason-bearing baseline at
``python/pylint-skip-file-baseline.json``. Inline suppressions cannot disarm
this gate (I-Gate-1 / G-Enf-2).
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import tokenize
from pathlib import Path

from larch.core import proc
from larch.lint.engine import Finding, LintRule, SourceFile, run_rule

RULE_ID = "pylint-skip-file"
SUPPRESSION_TOKEN = "lint-pylint-skip-file"
BASELINE_FILENAME = "pylint-skip-file-baseline.json"
SCOPE_PREFIX = "python/larch/"
SKIP_FILE_MESSAGE = "banned pylint skip-file directive"
DUPLICATE_CODE_MESSAGE = "banned module-level pylint disable of duplicate-code"
DUPLICATE_CODE_NAMES = frozenset({"r0801", "duplicate-code"})

_PYLINT_HEADER_RE = re.compile(r"^#\s*pylint\s*:\s*(.*)$", re.IGNORECASE)
_SKIP_FILE_RE = re.compile(r"^skip-file\b", re.IGNORECASE)
_DISABLE_RE = re.compile(
    r"^disable(?P<next>-next)?(?:\s*=\s*|\s+)(?P<body>.+)$",
    re.IGNORECASE,
)


def _in_scope(path: str) -> bool:
    return path.startswith(SCOPE_PREFIX) and path.endswith(".py")


def _split_directive_values(body: str) -> list[str]:
    primary = body.split("#", 1)[0]
    return [part.strip() for part in primary.split(",") if part.strip()]


def _comment_directives(source: SourceFile) -> list[tuple[int, int, str]]:
    """Return ``(lineno, column, comment_text)`` for each comment token."""
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source.text).readline)
        return [
            (token.start[0], token.start[1], token.string)
            for token in tokens
            if token.type == tokenize.COMMENT
        ]
    except tokenize.TokenError:
        return []
    except IndentationError:
        return []


def detect(source: SourceFile) -> list[Finding]:
    """Detect banned pylint skip-file / module-level duplicate-code disables."""
    if not source.is_python or not _in_scope(source.path):
        return []
    findings: list[Finding] = []
    for lineno, column, comment in _comment_directives(source):
        match = _PYLINT_HEADER_RE.match(comment)
        if match is None:
            continue
        payload = match.group(1).strip()
        if _SKIP_FILE_RE.match(payload) is not None:
            findings.append(
                Finding(
                    path=source.path,
                    line=lineno,
                    rule_id=RULE_ID,
                    message=SKIP_FILE_MESSAGE,
                )
            )
            continue
        disable = _DISABLE_RE.match(payload)
        if disable is None:
            continue
        if disable.group("next") is not None:
            continue
        if column != 0:
            # Indented disables are local / block-scoped, not module-wide.
            continue
        values = {value.casefold() for value in _split_directive_values(disable.group("body"))}
        if values & DUPLICATE_CODE_NAMES:
            findings.append(
                Finding(
                    path=source.path,
                    line=lineno,
                    rule_id=RULE_ID,
                    message=DUPLICATE_CODE_MESSAGE,
                )
            )
    return findings


RULE = LintRule(
    rule_id=RULE_ID,
    description=(
        "Ban pylint skip-file and module-level duplicate-code disables in "
        "python/larch/ runtime modules"
    ),
    detect=detect,
    syntax_policy="fail",
    suppression_token=SUPPRESSION_TOKEN,
    allow_inline_suppression=False,
)


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(
        prog="cli.py lint pylint-skip-file",
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
        help=f"Regenerate {BASELINE_FILENAME} from the live scan.",
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
    """CLI entry registered as ``python3 python/cli.py lint pylint-skip-file``."""
    parsed = _parse_args(argv if argv is not None else sys.argv[1:])
    if parsed is None:
        return 2
    root = Path(str(parsed.root)).resolve()
    baseline_path = root / "python" / BASELINE_FILENAME
    initial_reason = parsed.initial_reason
    if initial_reason is not None and not str(initial_reason).strip():
        print("lint-pylint-skip-file: --initial-reason must be non-empty", file=sys.stderr)
        return 2
    write_baseline = bool(parsed.write)
    # write_baseline forbids filtered paths; detect() self-scopes to python/larch/.
    paths: list[str] | None = None if write_baseline else [SCOPE_PREFIX.rstrip("/")]
    return run_rule(
        RULE,
        root,
        proc.ProcRunner(),
        paths=paths,
        baseline_path=baseline_path,
        write_baseline=write_baseline,
        initial_reason=None if initial_reason is None else str(initial_reason),
        strict_stale=not write_baseline,
    )


if __name__ == "__main__":
    raise SystemExit(main())
