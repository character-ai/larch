r"""Coverage for python/plan_review_round.py finding collection and classification.

Regression guard for issue #4790: ``collect_results`` emits ``KEY=VALUE`` blocks,
but ``_compose_findings_from_collector`` parsed ``\x1f``-delimited records, so every
reviewer finding was silently dropped and a real zero-collector round was reported
as a clean ``complete``.
"""

# pyright: reportPrivateUsage=false

from __future__ import annotations

from typing import TYPE_CHECKING

import collect_results
import plan_review_round

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _collector_text(records: list[collect_results.CollectorRecord]) -> str:
    """Mirror ``collect_results._emit_records``: KEY=VALUE per line, blank line between records."""
    blocks = ["\n".join(rec.fields()) for rec in records]
    return "\n\n".join(blocks) + "\n"


def _write_sidecar(path: Path, rows: list[dict[str, str]]) -> None:
    cols = ["scope", "severity", "focus_area", "location", "what", "scenario_or_breakage", "suggested_fix"]
    lines = ["\t".join(cols)]
    lines.extend("\t".join(row.get(col, "") for col in cols) for row in rows)
    _ = path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_compose_findings_parses_keyvalue_collector(tmp_path: Path) -> None:
    """A KEY=VALUE collector with OK reviewers yields parsed findings (issue #4790)."""
    design = tmp_path
    # Sidecar path differs from the ``{reviewer_file}.tsv`` fallback so the test also
    # proves STRUCTURED_SIDECAR is read by key (its emit order differs from the old
    # positional \x1f unpack, which placed FAILURE_REASON before STRUCTURED_SIDECAR).
    sidecar_in = design / "codex-plan-arch.sidecar.tsv"
    _write_sidecar(
        sidecar_in,
        [
            {
                "scope": "in_scope",
                "severity": "high",
                "focus_area": "correctness",
                "location": "python/x.py:10",
                "what": "Off-by-one in loop bound",
                "scenario_or_breakage": "iterates one element past the end",
                "suggested_fix": "use < instead of <=",
            }
        ],
    )
    sidecar_oos = design / "cursor-plan-pragmatic.sidecar.tsv"
    _write_sidecar(
        sidecar_oos,
        [
            {
                "scope": "out_of_scope",
                "severity": "nit",
                "focus_area": "style",
                "location": "python/y.py:5",
                "what": "Rename ambiguous variable",
                "scenario_or_breakage": "n/a",
                "suggested_fix": "rename tmp to record",
            }
        ],
    )
    records = [
        collect_results.CollectorRecord(
            reviewer_file=str(design / "codex-plan-arch-output.txt"),
            tool="codex",
            status="OK",
            exit_code="0",
            structured_sidecar=str(sidecar_in),
        ),
        collect_results.CollectorRecord(
            reviewer_file=str(design / "cursor-plan-pragmatic-output.txt"),
            tool="cursor",
            status="OK",
            exit_code="0",
            structured_sidecar=str(sidecar_oos),
        ),
    ]
    collect_text = _collector_text(records)
    manifest = design / "plan-review-slots.ndjson"  # absent: slot labels fall back to basename

    in_scope, oos_md, ok_count, fail_count = plan_review_round._compose_findings_from_collector(design, collect_text, manifest)

    assert ok_count == 2
    assert fail_count == 0
    assert "### FINDING_1:" in in_scope
    assert "Off-by-one in loop bound" in in_scope
    assert "### OOS_1:" in oos_md
    assert "Rename ambiguous variable" in oos_md


def test_compose_findings_empty_collector_text(tmp_path: Path) -> None:
    """Empty collector output yields zero OK records and no findings."""
    in_scope, oos_md, ok_count, fail_count = plan_review_round._compose_findings_from_collector(
        tmp_path, "", tmp_path / "plan-review-slots.ndjson"
    )
    assert ok_count == 0
    assert fail_count == 0
    assert in_scope == ""
    assert oos_md == ""


def test_compose_findings_counts_failures_without_dropping_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-OK reviewer is counted as a failure while OK reviewers still parse (issue #4790)."""
    # Failure records trigger collector-failure-log composition via _run_cli; stub it so
    # the unit test does not spawn the CLI subprocess.
    monkeypatch.setattr(plan_review_round, "_run_cli", lambda *_a, **_k: None)  # type: ignore[arg-type]
    design = tmp_path
    sidecar_ok = design / "codex-plan-arch.sidecar.tsv"
    _write_sidecar(
        sidecar_ok,
        [
            {
                "scope": "in_scope",
                "severity": "med",
                "focus_area": "correctness",
                "location": "python/z.py:1",
                "what": "Missing nil guard",
                "scenario_or_breakage": "crashes on empty input",
                "suggested_fix": "add guard",
            }
        ],
    )
    records = [
        collect_results.CollectorRecord(
            reviewer_file=str(design / "codex-plan-arch-output.txt"),
            tool="codex",
            status="OK",
            exit_code="0",
            structured_sidecar=str(sidecar_ok),
        ),
        collect_results.CollectorRecord(
            reviewer_file=str(design / "cursor-plan-arch-output.txt"),
            tool="cursor",
            status="TIMEOUT",
            exit_code="124",
            failure_reason="timed out",
        ),
    ]

    in_scope, _oos, ok_count, fail_count = plan_review_round._compose_findings_from_collector(
        design, _collector_text(records), design / "plan-review-slots.ndjson"
    )

    assert ok_count == 1
    assert fail_count == 1
    assert "Missing nil guard" in in_scope


def test_parse_collector_records_keyvalue_anchored() -> None:
    """parse_collector_records reads KEY=VALUE blocks by key and ignores leading diagnostics."""
    rec_a = collect_results.CollectorRecord(
        reviewer_file="/d/a-output.txt",
        tool="codex",
        status="OK",
        exit_code="0",
        structured_sidecar="/d/a.tsv",
    )
    rec_b = collect_results.CollectorRecord(
        reviewer_file="/d/b-output.txt",
        tool="cursor",
        status="TIMEOUT",
        exit_code="124",
        failure_reason="timed out",
    )
    body = "\n\n".join("\n".join(rec.fields()) for rec in (rec_a, rec_b)) + "\n"
    # A diagnostic line before the first REVIEWER_FILE anchor must not become a record.
    text = "collect-results: warning: dropping something basename=x.txt\n" + body

    parsed = collect_results.parse_collector_records(text)

    assert len(parsed) == 2
    assert parsed[0]["REVIEWER_FILE"] == "/d/a-output.txt"
    assert parsed[0]["STATUS"] == "OK"
    # Read by key: STRUCTURED_SIDECAR is emitted after EXIT_CODE, the opposite order
    # from the old positional \x1f unpack, so position-based parsing would mis-map it.
    assert parsed[0]["STRUCTURED_SIDECAR"] == "/d/a.tsv"
    assert parsed[1]["TOOL"] == "cursor"
    assert parsed[1]["FAILURE_REASON"] == "timed out"


def test_classify_zero_ok_collector_is_degraded_not_complete() -> None:
    """Secondary defect (issue #4790): a zero-OK round must never report ``complete``.

    Even when the voter panel dispatched fine (``degraded=False``), zero parsed
    collector records means no finding reached the ballot.
    """
    assert (
        plan_review_round._classify_round_loop_status(
            accepted=0, ok_count=0, degraded=False, panel_pruned_empty=False, tally_status="ok"
        )
        == "degraded-empty-collector"
    )


def test_classify_zero_ok_degraded_voter_is_degraded_empty() -> None:
    assert (
        plan_review_round._classify_round_loop_status(
            accepted=0, ok_count=0, degraded=True, panel_pruned_empty=False, tally_status="ok"
        )
        == "degraded-empty-collector"
    )


def test_classify_pruned_empty_panel_is_not_degraded_empty() -> None:
    """An intentionally pruned-empty panel is not the degraded-empty-collector failure."""
    assert (
        plan_review_round._classify_round_loop_status(
            accepted=0, ok_count=0, degraded=False, panel_pruned_empty=True, tally_status="ok"
        )
        == "complete"
    )


def test_classify_complete_when_findings_accepted() -> None:
    assert (
        plan_review_round._classify_round_loop_status(
            accepted=2, ok_count=3, degraded=False, panel_pruned_empty=False, tally_status="ok"
        )
        == "complete"
    )


def test_classify_zero_accepted_with_findings_is_zero_findings_degraded() -> None:
    """Reviewers ran (ok_count>0) but nothing was accepted and the panel degraded."""
    assert (
        plan_review_round._classify_round_loop_status(
            accepted=0, ok_count=4, degraded=True, panel_pruned_empty=False, tally_status="ok"
        )
        == "zero-findings-degraded-panel"
    )
