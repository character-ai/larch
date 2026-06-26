from __future__ import annotations

# pyright: reportUnusedCallResult=false

import csv
import json
from pathlib import Path

import pytest

import calibration_replay

REPO_ROOT = Path(__file__).resolve().parent.parent


def _write_jsonl(run_root: Path, records: list[dict[str, object]]) -> None:
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "review-findings-full.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )


def test_rebuild_single_item_ballot_from_jsonl(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path,
        [
            {
                "id": "FINDING_1",
                "round_num": "2",
                "category": "Required regression test missing",
                "prose_body": "## Required regression test missing\n\n- **Reviewer(s)**: codex-specialist-testing-output.txt\n- Body",
            }
        ],
    )

    ballot, source = calibration_replay.rebuild_single_item_ballot(finding_id="FINDING_1", run_root=tmp_path, round_num=2)

    assert source == "review_findings_jsonl"
    assert ballot.startswith("### FINDING_1: Required regression test missing\n\n")
    assert "## Required regression test missing" not in ballot
    assert "- **Reviewer(s)**: anonymous" in ballot


def test_rebuild_single_item_ballot_from_round_findings(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-1"
    round_dir.mkdir()
    (round_dir / "findings.md").write_text(
        "### FINDING_1: first\n\n- **Reviewer(s)**: cursor-specialist-output.txt\n\n"
        "### OOS_2: second\n\n- **Reviewer(s)**: codex-specialist-output.txt\n",
        encoding="utf-8",
    )

    ballot, source = calibration_replay.rebuild_single_item_ballot(finding_id="OOS_2", run_root=tmp_path, round_num=1)

    assert source == "round_findings"
    assert ballot.startswith("### OOS_2: second")
    assert "FINDING_1" not in ballot
    assert "- **Reviewer(s)**: anonymous" in ballot


def test_rebuild_single_item_ballot_prefers_fixture(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture.ballot.txt"
    fixture.write_text("### FINDING_7: frozen\n\n- **Reviewer(s)**: named\n", encoding="utf-8")

    ballot, source = calibration_replay.rebuild_single_item_ballot(
        finding_id="FINDING_7",
        run_root=tmp_path,
        round_num=1,
        fixture_ballot_path=fixture,
    )

    assert source == "fixture_ballot"
    assert ballot == "### FINDING_7: frozen\n\n- **Reviewer(s)**: anonymous\n"


def test_rebuild_single_item_ballot_fails_on_missing_jsonl_record(tmp_path: Path) -> None:
    _write_jsonl(tmp_path, [{"id": "FINDING_2", "round_num": "1", "prose_body": "body"}])

    with pytest.raises(calibration_replay.CalibrationReplayError, match="no ballot source"):
        calibration_replay.rebuild_single_item_ballot(finding_id="FINDING_1", run_root=tmp_path, round_num=1)


def test_rebuild_single_item_ballot_fails_on_truncated_jsonl_without_fixture(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path,
        [{"id": "FINDING_1", "round_num": "1", "category": "Long finding", "prose_body": "x" * 2000}],
    )

    with pytest.raises(calibration_replay.CalibrationReplayError, match="not production-parity"):
        calibration_replay.rebuild_single_item_ballot(finding_id="FINDING_1", run_root=tmp_path, round_num=1)


def test_rebuild_single_item_ballot_neutralizes_reviewer_attribution(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path,
        [
            {
                "id": "FINDING_1",
                "round_num": "1",
                "category": "Missing plan fixture",
                "prose_body": "- **Reviewer(s)**: cursor-specialist-testing-output.txt\n- Concern",
            }
        ],
    )

    ballot, _source = calibration_replay.rebuild_single_item_ballot(finding_id="FINDING_1", run_root=tmp_path, round_num=1)

    assert "- **Reviewer(s)**: anonymous" in ballot
    assert "cursor-specialist-testing-output" not in ballot


def test_extract_implementation_plan_from_plan_goals_test(tmp_path: Path) -> None:
    source = tmp_path / "plan-goals-test.md"
    source.write_text(
        "## Goal\nship it\n\n## Implementation Plan\nDo the thing.\n\n## Test plan\nRun tests.\n",
        encoding="utf-8",
    )

    assert calibration_replay.extract_implementation_plan_from_plan_goals_test(source) == "Do the thing.\n"


def test_extract_implementation_plan_fails_on_empty_body(tmp_path: Path) -> None:
    source = tmp_path / "plan-goals-test.md"
    source.write_text("## Implementation Plan\n\n## Test plan\nRun tests.\n", encoding="utf-8")

    with pytest.raises(calibration_replay.CalibrationReplayError, match="empty"):
        calibration_replay.extract_implementation_plan_from_plan_goals_test(source)


def test_extract_implementation_plan_fails_on_pointer_only_body(tmp_path: Path) -> None:
    source = tmp_path / "plan-goals-test.md"
    source.write_text("## Implementation Plan\nsee plan.txt\n", encoding="utf-8")

    with pytest.raises(calibration_replay.CalibrationReplayError, match="pointer-only"):
        calibration_replay.extract_implementation_plan_from_plan_goals_test(source)


def test_extract_implementation_plan_fails_on_pointer_first_line_with_trailing_content(tmp_path: Path) -> None:
    source = tmp_path / "plan-goals-test.md"
    source.write_text(
        "## Implementation Plan\nsee plan.txt\n\nActual plan content.\n\n## Test plan\nRun tests.\n",
        encoding="utf-8",
    )

    with pytest.raises(calibration_replay.CalibrationReplayError, match="pointer-only"):
        calibration_replay.extract_implementation_plan_from_plan_goals_test(source)


def test_load_fixture_plan_rejects_full_document_shape(tmp_path: Path) -> None:
    plan = tmp_path / "full.plan.txt"
    plan.write_text(
        "## Goal\nship it\n\n## Implementation Plan\nDo the thing.\n\n## Test plan\nRun tests.\n",
        encoding="utf-8",
    )

    with pytest.raises(calibration_replay.CalibrationReplayError, match="extracted Implementation Plan body"):
        calibration_replay.load_fixture_plan(plan)


def _manifest_row(**overrides: str) -> dict[str, str]:
    row = {
        "finding_id": "FINDING_1",
        "run_id": "RUN",
        "round_num": "1",
        "v2_tool": "codex-plan-fidelity",
        "v1_tool": "claude",
        "fixture_ballot": "",
        "fixture_plan": "fixtures/plan.txt",
        "fixture_diff": "",
        "diff_required": "false",
    }
    row.update(overrides)
    return row


def test_validate_manifest_row_fails_on_empty_fixture_plan(tmp_path: Path) -> None:
    with pytest.raises(calibration_replay.CalibrationReplayError, match="fixture_plan is required"):
        calibration_replay.validate_manifest_row(_manifest_row(fixture_plan=""), repo_root=tmp_path)


def test_validate_manifest_row_fails_on_missing_fixture_plan(tmp_path: Path) -> None:
    with pytest.raises(calibration_replay.CalibrationReplayError, match="fixture_plan"):
        calibration_replay.validate_manifest_row(_manifest_row(), repo_root=tmp_path)


def test_validate_manifest_row_fails_when_diff_required_without_fixture(tmp_path: Path) -> None:
    plan = tmp_path / "fixtures" / "plan.txt"
    plan.parent.mkdir()
    plan.write_text("Plan body\n", encoding="utf-8")

    with pytest.raises(calibration_replay.CalibrationReplayError, match="fixture_diff is required"):
        calibration_replay.validate_manifest_row(_manifest_row(diff_required="true"), repo_root=tmp_path)


def test_validate_manifest_row_passes_with_required_fixtures(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "plan.txt").write_text("Plan body\n", encoding="utf-8")
    (fixtures / "diff.patch").write_text("diff --git a/a b/a\n", encoding="utf-8")
    ballot = fixtures / "ballot.txt"
    ballot.write_text("### FINDING_1: frozen\n\n- **Reviewer(s)**: named\n", encoding="utf-8")
    run_root = tmp_path / "larch-logs" / "implement" / "RUN"
    run_root.mkdir(parents=True)

    calibration_replay.validate_manifest_row(
        _manifest_row(fixture_diff="fixtures/diff.patch", diff_required="true", fixture_ballot="fixtures/ballot.txt"),
        repo_root=tmp_path,
    )


def test_validate_manifest_row_fails_on_missing_run_id(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "plan.txt").write_text("Plan body\n", encoding="utf-8")

    with pytest.raises(calibration_replay.CalibrationReplayError, match="run_id and positive numeric round_num"):
        calibration_replay.validate_manifest_row(_manifest_row(run_id=""), repo_root=tmp_path)


def test_validate_manifest_row_fails_on_invalid_round_num(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "plan.txt").write_text("Plan body\n", encoding="utf-8")

    with pytest.raises(calibration_replay.CalibrationReplayError, match="run_id and positive numeric round_num"):
        calibration_replay.validate_manifest_row(_manifest_row(round_num="0"), repo_root=tmp_path)


def test_validate_manifest_row_fails_when_ballot_not_reconstructible(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "plan.txt").write_text("Plan body\n", encoding="utf-8")
    run_root = tmp_path / "larch-logs" / "implement" / "RUN"
    run_root.mkdir(parents=True)

    with pytest.raises(calibration_replay.CalibrationReplayError, match="no ballot source"):
        calibration_replay.validate_manifest_row(_manifest_row(), repo_root=tmp_path)


def test_validate_manifest_fails_when_manifest_missing_cohort_rows(tmp_path: Path) -> None:
    cohort = tmp_path / "cohort.tsv"
    cohort.write_text(
        "finding_id\trun_id\tround_num\tv2_tool\tv1_tool\n"
        "FINDING_1\tRUN\t1\tcodex-plan-fidelity\tclaude\n"
        "FINDING_2\tRUN2\t1\tcodex-plan-fidelity\tclaude\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.tsv"
    manifest.write_text(
        "finding_id\trun_id\tround_num\tv2_tool\tv1_tool\tfixture_ballot\tfixture_plan\tfixture_diff\tdiff_required\n"
        "FINDING_1\tRUN\t1\tcodex-plan-fidelity\tclaude\tfixtures/ballot.txt\tfixtures/plan.txt\t\tfalse\n",
        encoding="utf-8",
    )
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "plan.txt").write_text("Plan body\n", encoding="utf-8")
    (fixtures / "ballot.txt").write_text("### FINDING_1: frozen\n\n", encoding="utf-8")
    run_root = tmp_path / "larch-logs" / "implement" / "RUN"
    run_root.mkdir(parents=True)

    errors = calibration_replay.validate_manifest(manifest, repo_root=tmp_path, cohort_path=cohort)

    assert any("missing labeled cohort rows" in error for error in errors)


def test_committed_plan_fixtures_match_extractor() -> None:
    manifest = REPO_ROOT / calibration_replay.DEFAULT_MANIFEST
    rows = list(csv.DictReader(manifest.read_text(encoding="utf-8").splitlines(), delimiter="\t"))
    for row in rows:
        run_id = (row.get("run_id") or "").strip()
        plan_fixture = REPO_ROOT / (row.get("fixture_plan") or "")
        source = REPO_ROOT / "larch-logs" / "implement" / run_id / "plan-goals-test.md"
        assert plan_fixture.is_file(), f"missing fixture_plan: {plan_fixture}"
        assert source.is_file(), f"missing plan-goals-test.md for {run_id}"
        expected = calibration_replay.extract_implementation_plan_from_plan_goals_test(source)
        assert plan_fixture.read_text(encoding="utf-8") == expected


def test_run_replay_dry_run(tmp_path: Path) -> None:
    results = calibration_replay.run_replay(
        repo_root=REPO_ROOT,
        work_dir=tmp_path / "replay",
        manifest_path=REPO_ROOT / calibration_replay.DEFAULT_MANIFEST,
        cohort_path=REPO_ROOT / calibration_replay.DEFAULT_COHORT,
        dry_run=True,
    )

    assert len(results) == 4
    assert {row["finding_id"] for row in results} == {"FINDING_10", "FINDING_3", "FINDING_1"}
