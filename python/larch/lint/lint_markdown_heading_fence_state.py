"""Flag Markdown heading regexes applied to splitlines without fence state.

Thin engine-backed rule: detection lives in
``markdown_heading_fence_state_detector``. Grandfathered rows use
``python/markdown-heading-fence-state-baseline.json`` with the occurrence
codec. Mechanically backs G-Md-3 / #6676.
"""

from __future__ import annotations

import ast
import sys

from larch.core import proc
from larch.lint.engine import Finding, LintRule, RuleCli, SourceFile, run_rule_cli
from larch.lint.markdown_heading_fence_state_detector import (
    SUPPRESSION,
    is_production_source_path,
    scan_text,
)

RULE_ID = SUPPRESSION
BASELINE_FILENAME = "markdown-heading-fence-state-baseline.json"
PATHSPECS = ("python/*.py", "python/**/*.py")


def detect(source: SourceFile) -> list[Finding]:
    """Adapt detector hits into engine findings with occurrence identity."""
    if not source.is_python:
        return []
    tree = source.python_ast
    if not isinstance(tree, ast.Module):
        return []
    hits = scan_text(source.path, source.text, tree=tree)
    return [
        Finding(
            path=source.path,
            line=hit.lineno,
            rule_id=RULE_ID,
            message=(
                f"applies heading regex {hit.pattern_name} to splitlines "
                f"without fence-state gating (occurrence {hit.occurrence})"
            ),
            qualified_symbol=hit.qualified_symbol,
            pattern_name=hit.pattern_name,
            occurrence=hit.occurrence,
        )
        for hit in hits
    ]


RULE = LintRule(
    rule_id=RULE_ID,
    description=(
        "Flag Markdown heading regexes applied to splitlines without fence-state gating"
    ),
    detect=detect,
    syntax_policy="raise",
    suppression_token=SUPPRESSION,
    allow_inline_suppression=False,
    pathspecs=PATHSPECS,
    source_filter=is_production_source_path,
    occurrence_baseline=True,
    stale_baseline_on_clean_scan=True,
)


def main(argv: list[str] | None = None) -> int:
    """CLI entry registered as ``python3 python/cli.py lint markdown-heading-fence-state``."""
    return run_rule_cli(
        argv if argv is not None else sys.argv[1:],
        rule=RULE,
        cli=RuleCli(
            prog="cli.py lint markdown-heading-fence-state",
            description=__doc__,
            baseline_filename=BASELINE_FILENAME,
            error_label="lint-markdown-heading-fence-state",
        ),
        runner=proc.ProcRunner(),
    )


if __name__ == "__main__":
    raise SystemExit(main())
