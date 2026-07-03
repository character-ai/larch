from __future__ import annotations

# pyright: reportUnusedCallResult=false

import json
from pathlib import Path
from typing import Any

import pytest

from larch.calibration import difficulty
from larch.calibration import difficulty_calibration as dc
from larch.review import voting


DESIGN_HEADER = "finding_id\tfinding_reviewers\tvoting_result\tv1_vote\tv2_vote\tv3_vote\tscope\tbody_severity"
CODE_HEADER = voting.CODE_REVIEW_FINDINGS_CLASSIFICATION_HEADER
SIDECAR_HEADER = "schema_version\tfinding_hash\tsource_skill\trun_id\tround_num\tfinding_id\tdissenting_slots\tverdict\tcurrent_location\tevidence\ttriaged_at"


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "larch-logs"
    root.mkdir()
    return root


def _rating(applied: str, *, predicted: str | None = None, escalated: bool = False, audit: bool = False) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "rater": "implement",
        "rater_tool": "codex",
        "rater_model": "gpt-test",
        "predicted_tier": predicted or applied,
        "confidence": "medium",
        "rationale": "fixture",
        "design_tier": None,
        "implement_tier": None,
        "applied_tier": applied,
        "override_source": "none",
        "floors_applied": [],
        "audit_upgrade": "true" if audit else None,
        "audit_evaluated": audit,
        "escalations": [{"round": 1, "trigger": "fixture"}] if escalated else [],
        "panel_skipped": None,
    }


def _run(root: Path, skill: str, run_id: str, *, applied: str = difficulty.MODERATE, predicted: str | None = None, escalated: bool = False, audit: bool = False, month: str = "2026-06", issue: int = 42, rating: bool = True) -> Path:
    run = root / skill / run_id
    run.mkdir(parents=True)
    (run / "manifest.json").write_text(
        json.dumps({"started_at": f"{month}-15T10:00:00Z", "issue_number": issue, "skill": skill}),
        encoding="utf-8",
    )
    if rating:
        (run / "difficulty-rating.json").write_text(json.dumps(_rating(applied, predicted=predicted, escalated=escalated, audit=audit)), encoding="utf-8")
    (run / ("token-report-final.json" if skill == "design" else "token-report.json")).write_text(
        json.dumps({"BUCKETS_claude": {"input": 100, "cache_read": 0, "cache_create_5m": 0, "cache_create_1h": 0, "output": 10, "total": 110}}),
        encoding="utf-8",
    )
    (run / ("timing-report-final.json" if skill == "design" else "timing-report.json")).write_text(json.dumps({"total_seconds": 60}), encoding="utf-8")
    return run


def _design_row(fid: str, result: str, *, scope: str = "", severity: str = "blocker") -> str:
    return f"{fid}\treviewer\t{result}\tYES\tNO\tNO\t{scope}\t{severity}"


def _design_tsv(run: Path, round_num: int, *rows: str) -> None:
    path = run / "plan-review" / f"round-{round_num}" / "findings-classification.tsv"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(DESIGN_HEADER + "\n" + "\n".join(rows) + "\n", encoding="utf-8")


def _code_row(fid: str, result: str, *, scope: str = "", severity: str = "major") -> str:
    values = [
        fid,
        "reviewer",
        result,
        "YES",
        "true",
        severity,
        "good",
        "false",
        "cursor-validity",
        "NO",
        "true",
        "minor",
        "good",
        "false",
        "codex-plan-fidelity",
        "NO",
        "true",
        "minor",
        "good",
        "false",
        "codex-pragmatism",
        scope,
    ]
    return "\t".join(values)


def _implement_tsv(run: Path, round_num: int, *rows: str) -> None:
    path = run / f"round-{round_num}" / "findings-classification.tsv"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(CODE_HEADER + "\n" + "\n".join(rows) + "\n", encoding="utf-8")


def _review_tsv(run: Path, round_num: int, *rows: str) -> None:
    path = run / f"review-findings-classification-round-{round_num}.tsv"
    path.write_text(CODE_HEADER + "\n" + "\n".join(rows) + "\n", encoding="utf-8")


def _report(root: Path) -> tuple[dc.Corpus, str]:
    corpus = dc.collect_corpus(root)
    return corpus, dc.render_report(corpus)


def test_confusion_matrix_rows_for_all_three_skills(tmp_path: Path) -> None:
    root = _root(tmp_path)
    design_run = _run(root, "design", "DESIGN-0", applied=difficulty.TRIVIAL)
    _design_tsv(design_run, 1, _design_row("FINDING_1", "rejected"))
    impl_run = _run(root, "implement", "IMPL-1", applied=difficulty.MODERATE)
    _implement_tsv(impl_run, 1, _code_row("FINDING_1", "accepted"))
    review_run = _run(root, "review", "REV-3", applied=difficulty.HARD)
    _review_tsv(review_run, 1, _code_row("FINDING_1", "accepted"), _code_row("FINDING_2", "accepted"), _code_row("FINDING_3", "accepted"))

    _corpus, report = _report(root)

    assert "### design" in report
    assert "| TRIVIAL | 1 | 0 | 0 |" in report
    assert "### implement" in report
    assert "| MODERATE | 0 | 1 | 0 |" in report
    assert "### review" in report
    assert "| HARD | 0 | 0 | 1 |" in report


def test_realized_tier_formula_and_escalated_gc_slimmed_run(tmp_path: Path) -> None:
    root = _root(tmp_path)
    zero = _run(root, "implement", "ZERO", applied=difficulty.TRIVIAL)
    _implement_tsv(zero, 1, _code_row("FINDING_1", "rejected"))
    one = _run(root, "implement", "ONE", applied=difficulty.MODERATE)
    _implement_tsv(one, 1, _code_row("FINDING_1", "accepted"))
    three = _run(root, "implement", "THREE", applied=difficulty.HARD)
    _implement_tsv(three, 1, _code_row("FINDING_1", "accepted"), _code_row("FINDING_2", "accepted"), _code_row("FINDING_3", "accepted"))
    escalated = _run(root, "implement", "ESC", applied=difficulty.MODERATE, escalated=True)
    (escalated / "gc-slimmed").write_text("", encoding="utf-8")

    corpus, _report_text = _report(root)
    realized = {record.run_id: record.realized_tier for record in corpus.records}

    assert realized["ZERO"] == difficulty.TRIVIAL
    assert realized["ONE"] == difficulty.MODERATE
    assert realized["THREE"] == difficulty.HARD
    assert realized["ESC"] == difficulty.HARD


def test_design_identity_dedupes_and_highest_numeric_round_wins(tmp_path: Path) -> None:
    root = _root(tmp_path)
    run = _run(root, "design", "DESIGN-ID", applied=difficulty.MODERATE)
    _design_tsv(run, 1, _design_row("FINDING_1", "accepted"), _design_row("FINDING_2", "accepted"))
    _design_tsv(run, 2, _design_row("FINDING_1", "accepted"))
    _design_tsv(run, 10, _design_row("FINDING_2", "rejected"))

    corpus, _report_text = _report(root)
    record = next(item for item in corpus.records if item.run_id == "DESIGN-ID")

    assert record.classification.accepted_count == 1
    assert record.realized_tier == difficulty.MODERATE


def test_implement_identity_restarts_each_round(tmp_path: Path) -> None:
    root = _root(tmp_path)
    run = _run(root, "implement", "IMPL-ID", applied=difficulty.MODERATE)
    _implement_tsv(run, 1, _code_row("FINDING_1", "accepted"))
    _implement_tsv(run, 2, _code_row("FINDING_1", "accepted"))

    corpus, _report_text = _report(root)
    record = next(item for item in corpus.records if item.run_id == "IMPL-ID")

    assert record.classification.accepted_count == 2
    assert record.realized_tier == difficulty.MODERATE


def test_panel_kind_is_pinned_per_skill(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _root(tmp_path)
    design_run = _run(root, "design", "D")
    _design_tsv(design_run, 1, _design_row("FINDING_1", "accepted"))
    impl_run = _run(root, "implement", "I")
    _implement_tsv(impl_run, 1, _code_row("FINDING_1", "accepted"))
    review_run = _run(root, "review", "R")
    _review_tsv(review_run, 1, _code_row("FINDING_1", "accepted"))
    calls: list[str] = []
    original = voting.classification_row_panel_inputs

    def wrapper(text: str, *, panel_kind: str):
        calls.append(panel_kind)
        return original(text, panel_kind=panel_kind)

    monkeypatch.setattr(voting, "classification_row_panel_inputs", wrapper)

    dc.collect_corpus(root)

    assert calls == ["design", "code-review", "code-review"]


def test_severity_does_not_alter_realized_tier(tmp_path: Path) -> None:
    root = _root(tmp_path)
    run = _run(root, "implement", "SEV", applied=difficulty.MODERATE)
    _implement_tsv(run, 1, _code_row("FINDING_1", "accepted", severity="blocker"))

    corpus, _report_text = _report(root)
    record = next(item for item in corpus.records if item.run_id == "SEV")

    assert record.substantiality_proxy == "unknown"
    assert record.classification.accepted_count == 1
    assert record.realized_tier == difficulty.MODERATE


def test_missing_rating_is_unratable_and_does_not_crash(tmp_path: Path) -> None:
    root = _root(tmp_path)
    run = _run(root, "implement", "NO-RATING", rating=False)
    _implement_tsv(run, 1, _code_row("FINDING_1", "accepted"))

    corpus, report = _report(root)

    assert corpus.degraded["unratable_missing_rating"] == 1
    assert "| implement | 1 | 0 | 1 | 1 | 0 |" in report


def test_gc_slimmed_implement_recovers_root_jsonl_and_review_recovers_ndjson(tmp_path: Path) -> None:
    root = _root(tmp_path)
    impl = _run(root, "implement", "JSONL", applied=difficulty.MODERATE)
    (impl / "gc-slimmed").write_text("", encoding="utf-8")
    (impl / "review-findings-full.jsonl").write_text(
        json.dumps({"id": "FINDING_1", "phase": "code-review", "outcome": "accepted", "round_num": 1}) + "\n"
        + json.dumps({"id": "FINDING_2", "phase": "design", "outcome": "accepted", "round_num": 1}) + "\n",
        encoding="utf-8",
    )
    review = _run(root, "review", "NDJSON", applied=difficulty.MODERATE)
    (review / "review-findings.ndjson").write_text(json.dumps({"id": "FINDING_1", "phase": "code-review", "outcome": "accepted", "round_num": 1}) + "\n", encoding="utf-8")

    corpus, _report_text = _report(root)
    by_id = {record.run_id: record for record in corpus.records}

    assert by_id["JSONL"].classification.accepted_count == 1
    assert by_id["JSONL"].realized_tier == difficulty.MODERATE
    assert by_id["NDJSON"].classification.accepted_count == 1
    assert by_id["NDJSON"].realized_tier == difficulty.MODERATE


def test_missing_classification_source_is_unknown_and_excluded_from_matrix(tmp_path: Path) -> None:
    root = _root(tmp_path)
    _run(root, "implement", "UNKNOWN", applied=difficulty.HARD)

    corpus, report = _report(root)
    record = next(item for item in corpus.records if item.run_id == "UNKNOWN")

    assert record.realized_tier == "unknown"
    assert corpus.degraded["unknown_realized_tiers"] == 1
    assert "### implement" in report
    assert "Denominator: 0" in report


def test_audit_pairing_renders_deltas_and_na_when_no_peer(tmp_path: Path) -> None:
    root = _root(tmp_path)
    audited = _run(root, "implement", "AUDIT", applied=difficulty.HARD, predicted=difficulty.MODERATE, audit=True, month="2026-05")
    peer = _run(root, "implement", "PEER", applied=difficulty.MODERATE, predicted=difficulty.MODERATE, month="2026-05")
    no_peer = _run(root, "implement", "AUDIT-NOPEER", applied=difficulty.HARD, predicted=difficulty.HARD, audit=True, month="2026-06")
    for run in (audited, peer, no_peer):
        _implement_tsv(run, 1, _code_row("FINDING_1", "accepted"))
    (audited / "token-report.json").write_text(json.dumps({"BUCKETS_claude": {"total": 200}}), encoding="utf-8")
    (peer / "token-report.json").write_text(json.dumps({"BUCKETS_claude": {"total": 100}}), encoding="utf-8")

    _corpus, report = _report(root)

    assert "| implement | AUDIT | 2026-05 | MODERATE | 1 | 100 | 0 |" in report
    assert "| implement | AUDIT-NOPEER | 2026-06 | HARD | 0 | n/a | n/a |" in report


def test_under_rating_and_sidecar_burden(tmp_path: Path) -> None:
    root = _root(tmp_path)
    run = _run(root, "implement", "MISS", applied=difficulty.MODERATE, predicted=difficulty.MODERATE)
    _implement_tsv(run, 1, _code_row("FINDING_1", "accepted"), _code_row("FINDING_2", "accepted"), _code_row("FINDING_3", "accepted"))
    (root / "rejected-analysis-verdicts.tsv").write_text(
        SIDECAR_HEADER
        + "\n1\thash1\timplement\tMISS\t1\tFINDING_1\tv1\tstale\tloc\tevidence\t2026-01-01T00:00:00Z"
        + "\n1\thash1\timplement\tMISS\t1\tFINDING_1\tv1\tconfirmed\tloc\tevidence\t2026-01-02T00:00:00Z\n",
        encoding="utf-8",
    )

    corpus, report = _report(root)

    assert corpus.degraded["duplicate_sidecar_rows"] == 1
    assert "| implement | MISS | 42 | MODERATE | MODERATE | HARD | 3 | n/a | confirmed=1 |" in report


def test_out_writes_report_and_prints_only_report_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = _root(tmp_path)
    run = _run(root, "implement", "OUT", applied=difficulty.TRIVIAL)
    _implement_tsv(run, 1, _code_row("FINDING_1", "rejected"))
    out = tmp_path / "report.md"

    rc = dc.analyze_main(["--log-root", str(root), "--out", str(out)])
    captured = capsys.readouterr()

    assert rc == 0
    assert captured.out == f"REPORT_FILE={out}\n"
    assert captured.err == ""
    assert "# Difficulty Calibration" in out.read_text(encoding="utf-8")


def test_missing_log_root_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = dc.analyze_main(["--log-root", str(tmp_path / "missing")])
    captured = capsys.readouterr()

    assert rc == 2
    assert "--log-root is missing" in captured.err
# pyright: reportMissingParameterType=false, reportUnknownMemberType=false
# pyright: reportUnknownParameterType=false, reportUnknownVariableType=false
# pyright: reportUnusedCallResult=false
