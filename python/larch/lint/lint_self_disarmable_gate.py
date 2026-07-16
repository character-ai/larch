"""Flag hard gates that disarm themselves via author-controlled plan metadata.

Mechanically backs invariant I-Gate-1 (#6542, #6524): a size or publish trigger
must not be suppressed, replaced, or short-circuited solely by model-authored
optional metadata such as ``diff_added`` or ``mechanical_churn``. Metadata may
OR-combine into a trigger or soften presentation after the hard decision.

Engine rule wrapper. Requires Piece 1 (#6988) to land
``LintRule.prepare_corpus`` before ``run_rule`` will invoke corpus preparation.
"""

from __future__ import annotations

import argparse
import dataclasses as _dc
import sys
from collections.abc import Sequence
from pathlib import Path

from larch.core import proc
from larch.lint import self_disarmable_gate_detector as _detector
from larch.lint.engine import LintRule, SourceFile, parse_argparse_args, run_rule

# Re-exports for callers that import from this module.
Finding = _detector.Finding
ScanError = _detector.ScanError
MetadataResolution = _detector.MetadataResolution
scan_file = _detector.scan_file
resolve_optional_metadata = _detector.resolve_optional_metadata

SUPPRESSION = _detector.SUPPRESSION
TOOL_FAILURE_EXIT = 2

PATHSPECS = ("python/larch/design/*.py",)
_DESIGN_PREFIX = "python/larch/design/"


def _source_filter(path: str) -> bool:
    """Retain flat production modules directly under python/larch/design/."""
    if not path.startswith(_DESIGN_PREFIX):
        return False
    tail = path[len(_DESIGN_PREFIX):]
    return "/" not in tail and not tail.startswith("test_")


def _has_prepare_corpus() -> bool:
    """Return True when Piece 1 has landed ``LintRule.prepare_corpus``."""
    return any(f.name == "prepare_corpus" for f in _dc.fields(LintRule))


def build_rule() -> LintRule:
    """Build a fresh engine rule with corpus-preparation closure.

    Requires Piece 1: call ``_has_prepare_corpus()`` before invoking this.
    Raises ``TypeError`` if ``LintRule.prepare_corpus`` is absent.
    """
    state: list[_detector.PreparedCorpus | None] = [None]

    def _prepare(sources: Sequence[SourceFile]) -> None:
        state[0] = _detector.prepare_corpus(sources)

    def _detect(source: SourceFile) -> object:
        if state[0] is None:
            raise _detector.ScanError("prepare_corpus was not called before detect")
        return _detector.detect(source, prepared=state[0])

    return LintRule(
        rule_id=SUPPRESSION,
        description=(
            "Flag hard gates that disarm themselves via author-controlled "
            "plan metadata (I-Gate-1)."
        ),
        detect=_detect,
        syntax_policy="raise",
        suppression_token=SUPPRESSION,
        allow_inline_suppression=False,
        pathspecs=PATHSPECS,
        source_filter=_source_filter,
        require_baseline=False,
        prepare_corpus=_prepare,
    )


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(
        prog="cli.py lint self-disarmable-gate",
        description=__doc__,
    )
    _ = parser.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    return parse_argparse_args(parser, argv)


def main(argv: list[str] | None = None) -> int:
    parsed = _parse_args(argv if argv is not None else sys.argv[1:])
    if parsed is None:
        return TOOL_FAILURE_EXIT
    if not _has_prepare_corpus():
        print(
            "lint-self-disarmable-gate: dependency-not-met: "
            "LintRule.prepare_corpus absent; Piece 1 (#6988) must land first",
            file=sys.stderr,
        )
        return TOOL_FAILURE_EXIT
    root = Path(str(parsed.root)).resolve()
    return run_rule(
        build_rule(),
        root,
        proc.ProcRunner(),
    )


if __name__ == "__main__":
    raise SystemExit(main())
