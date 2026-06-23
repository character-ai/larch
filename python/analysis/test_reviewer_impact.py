"""Tests for analysis.reviewer_impact."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from analysis import reviewer_impact as ri

_TSV_HEADER = (
    "finding_id\treviewer_slots\tvoting_result\t"
    "v1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv1_tool\t"
    "v2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv2_tool\t"
    "v3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain\tv3_tool"
)


def _row(fid: str, sev1: str, vote3: str, sev3: str) -> str:
    """One classification row: v1/v2 vote YES at sev1, v3 votes vote3 at sev3."""
    return (
        f"{fid}\tx\taccepted\t"
        f"YES\ttrue\t{sev1}\tgood\tfalse\tcursor-validity\t"
        f"YES\ttrue\t{sev1}\tgood\tfalse\tcursor-plan-fidelity\t"
        f"{vote3}\ttrue\t{sev3}\tgood\tfalse\tcursor-pragmatism"
    )


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")


def _make_run(root: Path) -> None:
    run = root / "RUN1"
    manifest_rows: list[dict[str, str]] = [
        {"slot": "correctness", "tool": "cursor", "output": "/t/round-1/cursor-specialist-correctness-output.txt"},
        {"slot": "correctness", "tool": "codex", "output": "/t/round-1/codex-specialist-correctness-output.txt"},
        {"slot": "dyn-x", "tool": "cursor", "output": "/t/round-1/dyn-x-output.txt"},
        {"slot": "dyn-x-codex", "tool": "codex", "output": "/t/round-1/dyn-x-codex-output.txt"},
    ]
    _write(
        run / "round-1" / "panel-manifest.ndjson",
        "".join(json.dumps(row) + "\n" for row in manifest_rows),
    )
    tsv = "\n".join([
        _TSV_HEADER,
        _row("FINDING_1", "major", "NO", "minor"),    # codex-unique -> panel major (YES majority)
        _row("FINDING_2", "minor", "YES", "minor"),   # cursor-unique -> panel minor
        _row("FINDING_3", "blocker", "YES", "blocker"),  # shared
    ])
    _write(run / "round-1" / "findings-classification.tsv", tsv + "\n")
    findings: list[dict[str, Any]] = [
        {"id": "FINDING_1", "phase": "code-review", "outcome": "accepted", "round_num": "1",
         "category": "codex only", "reviewer_slots": ["codex-specialist-correctness-output.txt"],
         "prose_body": "**Severity**: important"},
        {"id": "FINDING_2", "phase": "code-review", "outcome": "accepted", "round_num": "1",
         "category": "cursor only", "reviewer_slots": ["cursor-specialist-correctness-output.txt"],
         "prose_body": "**Severity**: nit"},
        {"id": "FINDING_3", "phase": "code-review", "outcome": "accepted", "round_num": "1",
         "category": "shared", "reviewer_slots": [
             "codex-specialist-correctness-output.txt", "cursor-specialist-correctness-output.txt"],
         "prose_body": "**Severity**: blocking"},
        {"id": "FINDING_4", "phase": "code-review", "outcome": "accepted", "round_num": "1",
         "category": "opaque", "reviewer_slots": ["panel"], "prose_body": ""},
        {"id": "FINDING_5", "phase": "code-review", "outcome": "rejected", "round_num": "1",
         "category": "rejected", "reviewer_slots": ["codex-specialist-correctness-output.txt"], "prose_body": ""},
        {"id": "FINDING_6", "phase": "code-review", "outcome": "out_of_scope", "round_num": "1",
         "category": "oos", "reviewer_slots": ["codex-specialist-correctness-output.txt"], "prose_body": ""},
    ]
    _write(
        run / "review-findings-full.jsonl",
        "".join(json.dumps(obj) + "\n" for obj in findings),
    )


def test_scan_coverage(tmp_path: Path) -> None:
    _make_run(tmp_path)
    data = ri.scan(tmp_path)
    assert data.coverage.runs_total == 1
    assert data.coverage.runs_with_findings == 1
    assert data.coverage.runs_with_manifest == 1
    assert data.opaque_accepted == 1  # the `panel` row is unattributable
    assert data.run_present["RUN1"] == frozenset({"codex", "cursor"})


def test_codex_unique_with_panel_severity(tmp_path: Path) -> None:
    _make_run(tmp_path)
    data = ri.scan(tmp_path)
    summ = ri.summarize(data, "codex", max_examples=10)
    assert summ.runs.head_to_head == 1
    assert summ.venn.unique == 1          # FINDING_1 only
    assert summ.venn.shared == 1          # FINDING_3 both
    assert summ.panel_severity == {"major": 1}
    assert summ.focus == {"correctness": 1}


def test_cursor_unique(tmp_path: Path) -> None:
    _make_run(tmp_path)
    data = ri.scan(tmp_path)
    summ = ri.summarize(data, "cursor", max_examples=10)
    assert summ.venn.unique == 1          # FINDING_2 only
    assert summ.panel_severity == {"minor": 1}


def test_claude_absent_is_empty(tmp_path: Path) -> None:
    _make_run(tmp_path)
    data = ri.scan(tmp_path)
    summ = ri.summarize(data, "claude", max_examples=10)
    assert summ.runs.head_to_head == 0
    assert summ.venn.unique == 0


def test_resolve_tool_manifest_and_heuristic() -> None:
    manifest = {"dyn-x-output.txt": "cursor", "dyn-x-codex-output.txt": "codex"}
    assert ri.resolve_tool("dyn-x-output.txt", manifest) == "cursor"
    assert ri.resolve_tool("dyn-x-codex-output.txt", manifest) == "codex"
    # heuristic fallback (no manifest): a dyn slot whose name references claude as
    # its review SUBJECT must not be misread as a claude reviewer.
    assert ri.resolve_tool("dyn-lint-claude-output.txt", {}) == "cursor"
    assert ri.resolve_tool("codex-specialist-correctness-output.txt", {}) == "codex"
    assert ri.resolve_tool("LEGACY:cursor-specialist-testing-output.txt", {}) == "cursor"
    assert ri.resolve_tool("panel", {}) == "unknown"


def test_modal_severity_tie_breaks_high() -> None:
    assert ri.modal_severity(["major", "major", "minor"]) == "major"
    assert ri.modal_severity(["minor", "blocker"]) == "blocker"  # tie -> higher
    assert ri.modal_severity([]) is None
    assert ri.modal_severity(["bogus"]) is None


def test_prose_severity() -> None:
    assert ri.prose_severity("lead **Severity**: important rest") == "important"
    assert ri.prose_severity("**Severity**: blocking") == "blocking"
    assert ri.prose_severity("no marker here") == "(unlabeled)"
    assert ri.prose_severity("**Severity**: wat") == "(unlabeled)"
