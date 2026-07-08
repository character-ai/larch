from __future__ import annotations

# pyright: reportUnusedCallResult=false, reportPrivateUsage=false

import csv
import json
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest

from larch.calibration import calibration_replay

REPO_ROOT = Path(__file__).resolve().parents[3]
TEST_RUN_ID = "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"


def _ballots_dir(tmp_path: Path) -> Path:
    ballots = tmp_path / calibration_replay.DEFAULT_BALLOTS_DIR
    ballots.mkdir(parents=True, exist_ok=True)
    return ballots


def _plans_dir(tmp_path: Path) -> Path:
    plans = tmp_path / calibration_replay.DEFAULT_PLANS_DIR
    plans.mkdir(parents=True, exist_ok=True)
    return plans


def _diffs_dir(tmp_path: Path) -> Path:
    diffs = tmp_path / calibration_replay.DEFAULT_DIFFS_DIR
    diffs.mkdir(parents=True, exist_ok=True)
    return diffs


def _write_plan_fixture(tmp_path: Path, text: str = "Plan body\n", *, name: str = "plan.txt") -> Path:
    plan = _plans_dir(tmp_path) / name
    plan.write_text(text, encoding="utf-8")
    return plan


def _write_diff_fixture(tmp_path: Path, text: str = "diff --git a/a b/a\n", *, name: str = "diff.patch") -> Path:
    diff = _diffs_dir(tmp_path) / name
    diff.write_text(text, encoding="utf-8")
    return diff


def _write_classification_tsv(
    tmp_path: Path,
    *,
    run_id: str = TEST_RUN_ID,
    round_num: int = 1,
    rows: list[tuple[str, str, str, str, str]] | None = None,
) -> None:
    round_dir = tmp_path / "larch-logs" / "implement" / run_id / f"round-{round_num}"
    round_dir.mkdir(parents=True, exist_ok=True)
    lines = ["finding_id\tv2_vote\tv1_vote\tv3_vote\tvoting_result\tscope"]
    for finding_id, v2_vote, v1_vote, v3_vote, voting_result in rows or [
        ("FINDING_1", "NO", "NO", "NO", "rejected"),
    ]:
        lines.append(f"{finding_id}\t{v2_vote}\t{v1_vote}\t{v3_vote}\t{voting_result}\tin_scope")
    (round_dir / "findings-classification.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")


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


def test_extract_implementation_plan_from_plan_goals_test_preserves_issue_comment_step(
    tmp_path: Path,
) -> None:
    source = tmp_path / "plan-goals-test.md"
    source.write_text(
        "## Goal\nship it\n\n## Implementation Plan\n"
        "- During /implement, after tests pass, post one correcting comment on #6591 with "
        "`gh issue comment 6591 --body-file <body-file>`.\n"
        "- Verify the comment with `gh issue view 6591 --comments`.\n\n"
        "## Test plan\nRun tests.\n",
        encoding="utf-8",
    )

    plan = calibration_replay.extract_implementation_plan_from_plan_goals_test(source)

    assert "gh issue comment 6591 --body-file <body-file>" in plan
    assert "gh issue view 6591 --comments" in plan


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


def test_load_fixture_plan_rejects_pointer_only_body(tmp_path: Path) -> None:
    plan = _write_plan_fixture(tmp_path, "see plan.txt\n")

    with pytest.raises(calibration_replay.CalibrationReplayError, match="pointer-only"):
        calibration_replay.load_fixture_plan(plan)


def test_load_fixture_plan_rejects_full_document_shape(tmp_path: Path) -> None:
    plan = _write_plan_fixture(
        tmp_path,
        "## Goal\nship it\n\n## Implementation Plan\nDo the thing.\n\n## Test plan\nRun tests.\n",
        name="full.plan.txt",
    )

    with pytest.raises(calibration_replay.CalibrationReplayError, match="extracted Implementation Plan body"):
        calibration_replay.load_fixture_plan(plan)


def _manifest_row(**overrides: str) -> dict[str, str]:
    row = {
        "finding_id": "FINDING_1",
        "run_id": TEST_RUN_ID,
        "round_num": "1",
        "v2_tool": "codex-plan-fidelity",
        "v1_tool": "claude",
        "fixture_ballot": "",
        "fixture_plan": "python/test_fixtures/plan-fidelity-calibration/plans/plan.txt",
        "fixture_diff": "",
        "diff_required": "false",
    }
    row.update(overrides)
    return row


def _plan_rel(tmp_path: Path, text: str = "Plan body\n") -> str:
    return str(_write_plan_fixture(tmp_path, text).relative_to(tmp_path))


def _diff_rel(tmp_path: Path, text: str = "diff --git a/a b/a\n") -> str:
    return str(_write_diff_fixture(tmp_path, text).relative_to(tmp_path))


def _write_run_jsonl(
    tmp_path: Path,
    *,
    run_id: str = TEST_RUN_ID,
    records: list[dict[str, object]] | None = None,
) -> Path:
    run_root = tmp_path / "larch-logs" / "implement" / run_id
    _write_jsonl(
        run_root,
        records
        or [{"id": "FINDING_1", "round_num": "1", "category": "title", "prose_body": "### FINDING_1: title\n\nbody\n"}],
    )
    return run_root


def test_validate_manifest_row_fails_on_empty_fixture_plan(tmp_path: Path) -> None:
    with pytest.raises(calibration_replay.CalibrationReplayError, match="fixture_plan is required"):
        calibration_replay.validate_manifest_row(_manifest_row(fixture_plan=""), repo_root=tmp_path)


def test_validate_manifest_row_fails_on_missing_fixture_plan(tmp_path: Path) -> None:
    with pytest.raises(calibration_replay.CalibrationReplayError, match="fixture_plan"):
        calibration_replay.validate_manifest_row(_manifest_row(), repo_root=tmp_path)


def test_validate_manifest_row_fails_when_diff_required_without_fixture(tmp_path: Path) -> None:
    _write_plan_fixture(tmp_path)

    with pytest.raises(calibration_replay.CalibrationReplayError, match="fixture_diff is required"):
        calibration_replay.validate_manifest_row(_manifest_row(diff_required="true"), repo_root=tmp_path)


def test_validate_manifest_row_passes_with_required_fixtures(tmp_path: Path) -> None:
    plan_rel = _plan_rel(tmp_path)
    diff_rel = _diff_rel(tmp_path)
    ballots = _ballots_dir(tmp_path)
    ballot = ballots / "ballot.txt"
    ballot.write_text("### FINDING_1: frozen\n\n- **Reviewer(s)**: named\n", encoding="utf-8")
    _write_classification_tsv(tmp_path)
    _write_run_jsonl(tmp_path)
    ballot_rel = str(ballot.relative_to(tmp_path))

    calibration_replay.validate_manifest_row(
        _manifest_row(
            fixture_plan=plan_rel,
            fixture_diff=diff_rel,
            diff_required="true",
            fixture_ballot=ballot_rel,
        ),
        repo_root=tmp_path,
    )


def test_validate_manifest_row_fails_on_missing_run_id(tmp_path: Path) -> None:
    _write_plan_fixture(tmp_path)

    with pytest.raises(calibration_replay.CalibrationReplayError, match="run_id and positive numeric round_num"):
        calibration_replay.validate_manifest_row(_manifest_row(run_id=""), repo_root=tmp_path)


def test_validate_manifest_row_fails_on_invalid_round_num(tmp_path: Path) -> None:
    _write_plan_fixture(tmp_path)

    with pytest.raises(calibration_replay.CalibrationReplayError, match="run_id and positive numeric round_num"):
        calibration_replay.validate_manifest_row(_manifest_row(round_num="0"), repo_root=tmp_path)


def test_validate_manifest_row_fails_when_ballot_not_reconstructible(tmp_path: Path) -> None:
    _write_plan_fixture(tmp_path)
    _write_classification_tsv(tmp_path)

    with pytest.raises(calibration_replay.CalibrationReplayError, match="no ballot source"):
        calibration_replay.validate_manifest_row(_manifest_row(fixture_plan=_plan_rel(tmp_path)), repo_root=tmp_path)


def test_validate_manifest_fails_when_manifest_missing_cohort_rows(tmp_path: Path) -> None:
    cohort = tmp_path / "cohort.tsv"
    cohort.write_text(
        "finding_id\trun_id\tround_num\tv2_tool\tv1_tool\n"
        f"FINDING_1\t{TEST_RUN_ID}\t1\tcodex-plan-fidelity\tclaude\n"
        "FINDING_2\tBBBBBBBB-BBBB-BBBB-BBBB-BBBBBBBBBBBB\t1\tcodex-plan-fidelity\tclaude\n",
        encoding="utf-8",
    )
    plan_rel = _plan_rel(tmp_path)
    ballots = _ballots_dir(tmp_path)
    ballot = ballots / "ballot.txt"
    ballot.write_text("### FINDING_1: frozen\n\n", encoding="utf-8")
    ballot_rel = str(ballot.relative_to(tmp_path))
    _write_classification_tsv(tmp_path)
    _write_run_jsonl(tmp_path)
    manifest = tmp_path / "manifest.tsv"
    manifest.write_text(
        "finding_id\trun_id\tround_num\tv2_tool\tv1_tool\tfixture_ballot\tfixture_plan\tfixture_diff\tdiff_required\n"
        f"FINDING_1\t{TEST_RUN_ID}\t1\tcodex-plan-fidelity\tclaude\t{ballot_rel}\t{plan_rel}\t\tfalse\n",
        encoding="utf-8",
    )

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
    assert all(row.get("fixture_diff") for row in results)


def test_validate_manifest_row_rejects_fixture_diff_when_not_required(tmp_path: Path) -> None:
    plan_rel = _plan_rel(tmp_path)
    diff_rel = _diff_rel(tmp_path)
    _write_run_jsonl(tmp_path)

    with pytest.raises(calibration_replay.CalibrationReplayError, match="fixture_diff must be empty"):
        calibration_replay.validate_manifest_row(
            _manifest_row(fixture_plan=plan_rel, fixture_diff=diff_rel, diff_required="false"),
            repo_root=tmp_path,
        )


def test_validate_manifest_row_requires_readable_fixture_ballot(tmp_path: Path) -> None:
    plan_rel = _plan_rel(tmp_path)
    _write_run_jsonl(tmp_path)

    with pytest.raises(calibration_replay.CalibrationReplayError, match="fixture_ballot is not readable"):
        calibration_replay.validate_manifest_row(
            _manifest_row(
                fixture_plan=plan_rel,
                fixture_ballot="python/test_fixtures/plan-fidelity-calibration/ballots/missing.ballot.txt",
            ),
            repo_root=tmp_path,
        )


def test_validate_manifest_row_rejects_vote_tally_in_fixture_ballot(tmp_path: Path) -> None:
    plan_rel = _plan_rel(tmp_path)
    ballots = _ballots_dir(tmp_path)
    ballot = ballots / "ballot.txt"
    ballot.write_text("### FINDING_1: frozen\n\nbody\n\nVote tally: YES=1 NO=2 JUDGE_ERROR=0\n", encoding="utf-8")
    ballot_rel = str(ballot.relative_to(tmp_path))
    _write_classification_tsv(tmp_path)
    _write_run_jsonl(tmp_path)

    with pytest.raises(calibration_replay.CalibrationReplayError, match="historical vote tally"):
        calibration_replay.validate_manifest_row(
            _manifest_row(fixture_plan=plan_rel, fixture_ballot=ballot_rel),
            repo_root=tmp_path,
        )


def test_jsonl_record_requires_exact_id_and_round(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path,
        [
            {
                "id": "FINDING_2",
                "round_num": "1",
                "category": "quotes heading",
                "prose_body": "### FINDING_1: quoted heading\n\nbody\n",
            }
        ],
    )

    assert calibration_replay._jsonl_record(run_root=tmp_path, finding_id="FINDING_1", round_num=1) is None


def test_validate_manifest_rejects_duplicate_cohort_keys(tmp_path: Path) -> None:
    cohort = tmp_path / "cohort.tsv"
    cohort.write_text(
        "finding_id\trun_id\tround_num\tv2_tool\tv1_tool\n"
        f"FINDING_1\t{TEST_RUN_ID}\t1\tcodex-plan-fidelity\tclaude\n"
        f"FINDING_1\t{TEST_RUN_ID}\t1\tcodex-plan-fidelity\tclaude\n",
        encoding="utf-8",
    )
    plan_rel = _plan_rel(tmp_path)
    ballots = _ballots_dir(tmp_path)
    ballot = ballots / "ballot.txt"
    ballot.write_text("### FINDING_1: frozen\n\n", encoding="utf-8")
    ballot_rel = str(ballot.relative_to(tmp_path))
    _write_classification_tsv(tmp_path)
    _write_run_jsonl(tmp_path)
    manifest = tmp_path / "manifest.tsv"
    manifest.write_text(
        "finding_id\trun_id\tround_num\tv2_tool\tv1_tool\tfixture_ballot\tfixture_plan\tfixture_diff\tdiff_required\n"
        f"FINDING_1\t{TEST_RUN_ID}\t1\tcodex-plan-fidelity\tclaude\t{ballot_rel}\t{plan_rel}\t\tfalse\n",
        encoding="utf-8",
    )

    errors = calibration_replay.validate_manifest(manifest, repo_root=tmp_path, cohort_path=cohort)

    assert any("duplicate labeled cohort keys" in error for error in errors)


def test_dispatch_voters_for_row_fails_on_missing_parse_rate_status(tmp_path: Path) -> None:
    repo_root = tmp_path
    (repo_root / "python").mkdir()
    (repo_root / "python" / "cli.py").write_text("# stub\n", encoding="utf-8")
    ballot = tmp_path / "ballot.txt"
    ballot.write_text("### FINDING_1: title\n", encoding="utf-8")
    plan = tmp_path / "plan.txt"
    plan.write_text("Plan body\n", encoding="utf-8")
    dispatch_stdout = (
        "VOTER_2_STATUS=launched\n"
        "VOTER_2_TOOL=codex-plan-fidelity\n"
        "VOTER_2_PATH=codex-plan-fidelity-vote-output.txt"
    )

    class _Result:
        returncode = 0
        stdout = dispatch_stdout
        stderr = ""

    with patch("larch.calibration.calibration_replay.proc.run", return_value=_Result()):
        with pytest.raises(calibration_replay.CalibrationReplayError, match="VOTER_2_PARSE_RATE_STATUS"):
            calibration_replay._dispatch_voters_for_row(
                repo_root=repo_root,
                row=_manifest_row(),
                ballot_path=ballot,
                plan_path=plan,
                diff_path=None,
            )


def test_dispatch_voters_for_row_pins_feedback_off_and_skips_snapshot(tmp_path: Path) -> None:
    repo_root = tmp_path
    (repo_root / "python").mkdir()
    (repo_root / "python" / "cli.py").write_text("# stub\n", encoding="utf-8")
    ballot = tmp_path / "ballot.txt"
    ballot.write_text("### FINDING_1: title\n", encoding="utf-8")
    plan = tmp_path / "plan.txt"
    plan.write_text("Plan body\n", encoding="utf-8")
    dispatch_stdout = (
        "VOTER_2_STATUS=launched\n"
        "VOTER_2_TOOL=codex-plan-fidelity\n"
        "VOTER_2_PATH=codex-plan-fidelity-vote-output.txt\n"
        "VOTER_2_PARSE_RATE_STATUS=OK\n"
    )
    captured: list[tuple[list[str], dict[str, str]]] = []

    class _Result:
        returncode = 0
        stdout = dispatch_stdout
        stderr = ""

    def _fake_run(argv: list[str], **kwargs: object) -> _Result:
        env = cast("dict[str, str]", kwargs.get("env") or {})
        captured.append(([str(item) for item in argv], env))
        return _Result()

    with patch("larch.calibration.calibration_replay.proc.run", side_effect=_fake_run):
        calibration_replay._dispatch_voters_for_row(
            repo_root=repo_root,
            row=_manifest_row(),
            ballot_path=ballot,
            plan_path=plan,
            diff_path=None,
        )
    assert captured
    assert captured[0][1].get("LARCH_VOTER_CALIBRATION_FEEDBACK") == "0"
    assert not any("voter-calibration" in call[0] and "snapshot" in call[0] for call, _env in captured)


def test_parse_slot_v2_vote_reads_emitted_output(tmp_path: Path) -> None:
    voter = tmp_path / "codex-plan-fidelity-vote-output.txt"
    voter.write_text("FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n", encoding="utf-8")

    assert calibration_replay._parse_slot_v2_vote(voter_path=voter, finding_id="FINDING_1") == "YES"


def test_run_replay_parses_after_vote_with_mocked_dispatch(tmp_path: Path) -> None:
    plan_rel = _plan_rel(tmp_path)
    diff_rel = _diff_rel(tmp_path)
    ballots = _ballots_dir(tmp_path)
    ballot = ballots / "ballot.txt"
    ballot.write_text("### FINDING_1: frozen\n\nbody\n", encoding="utf-8")
    ballot_rel = str(ballot.relative_to(tmp_path))
    cohort = tmp_path / "cohort.tsv"
    cohort.write_text(
        "finding_id\trun_id\tround_num\tv2_tool\tv1_tool\n"
        f"FINDING_1\t{TEST_RUN_ID}\t1\tcodex-plan-fidelity\tclaude\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.tsv"
    manifest.write_text(
        "finding_id\trun_id\tround_num\tv2_tool\tv1_tool\tfixture_ballot\tfixture_plan\tfixture_diff\tdiff_required\n"
        f"FINDING_1\t{TEST_RUN_ID}\t1\tcodex-plan-fidelity\tclaude\t{ballot_rel}\t{plan_rel}\t{diff_rel}\ttrue\n",
        encoding="utf-8",
    )
    _write_classification_tsv(tmp_path)
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "python").mkdir()
    (repo_root / "python" / "cli.py").write_text("# stub\n", encoding="utf-8")
    for rel in (
        plan_rel,
        ballot_rel,
        diff_rel,
        f"larch-logs/implement/{TEST_RUN_ID}/round-1/findings-classification.tsv",
    ):
        target = repo_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text((tmp_path / rel).read_text(encoding="utf-8"), encoding="utf-8")
    _write_run_jsonl(repo_root)

    dispatch_stdout = (
        "VOTER_2_STATUS=launched\n"
        "VOTER_2_PARSE_RATE_STATUS=OK\n"
        "VOTER_2_TOOL=codex-plan-fidelity\n"
        "VOTER_2_PATH=codex-plan-fidelity-vote-output.txt"
    )

    class _Result:
        returncode = 0
        stdout = dispatch_stdout
        stderr = ""

    def _fake_run(argv: object, **_kwargs: object) -> _Result:
        argv_list = [str(part) for part in cast("list[str]", argv)]
        review_tmpdir = Path(argv_list[argv_list.index("--review-tmpdir") + 1])
        (review_tmpdir / "codex-plan-fidelity-vote-output.txt").write_text(
            "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n",
            encoding="utf-8",
        )
        return _Result()

    with patch("larch.calibration.calibration_replay.proc.run", side_effect=_fake_run):
        results = calibration_replay.run_replay(
            repo_root=repo_root,
            work_dir=tmp_path / "replay",
            manifest_path=manifest,
            cohort_path=cohort,
            dry_run=False,
        )

    assert results[0]["after_vote"] == "YES"
    assert results[0]["before_vote"] == "NO"


def test_committed_fixture_ballots_have_no_vote_tally() -> None:
    manifest = REPO_ROOT / calibration_replay.DEFAULT_MANIFEST
    rows = list(csv.DictReader(manifest.read_text(encoding="utf-8").splitlines(), delimiter="\t"))
    for row in rows:
        ballot_path = REPO_ROOT / (row.get("fixture_ballot") or "")
        text = ballot_path.read_text(encoding="utf-8")
        assert "Vote tally:" not in text, f"vote tally footer in {ballot_path}"


def test_before_vote_rejects_invalid_v2_vote(tmp_path: Path) -> None:
    _write_classification_tsv(tmp_path, rows=[("FINDING_1", "", "", "", "rejected")])

    with pytest.raises(calibration_replay.CalibrationReplayError, match="invalid v2_vote"):
        calibration_replay._before_vote(repo_root=tmp_path, row=_manifest_row())


def test_validate_manifest_row_rejects_invalid_v2_vote(tmp_path: Path) -> None:
    plan_rel = _plan_rel(tmp_path)
    _write_classification_tsv(tmp_path, rows=[("FINDING_1", "MAYBE", "NO", "NO", "rejected")])
    _write_run_jsonl(tmp_path)

    with pytest.raises(calibration_replay.CalibrationReplayError, match="invalid v2_vote"):
        calibration_replay.validate_manifest_row(_manifest_row(fixture_plan=plan_rel), repo_root=tmp_path)


def test_validate_manifest_row_rejects_ballot_outside_ballots_dir(tmp_path: Path) -> None:
    plan_rel = _plan_rel(tmp_path)
    outside = tmp_path / "outside.ballot.txt"
    outside.write_text("### FINDING_1: frozen\n\n", encoding="utf-8")
    _write_classification_tsv(tmp_path)
    _write_run_jsonl(tmp_path)

    with pytest.raises(calibration_replay.CalibrationReplayError, match="must be under"):
        calibration_replay.validate_manifest_row(
            _manifest_row(fixture_plan=plan_rel, fixture_ballot="outside.ballot.txt"),
            repo_root=tmp_path,
        )


def test_validate_manifest_row_rejects_mismatched_ballot_heading(tmp_path: Path) -> None:
    plan_rel = _plan_rel(tmp_path)
    ballots = _ballots_dir(tmp_path)
    ballot = ballots / "ballot.txt"
    ballot.write_text("### FINDING_2: frozen\n\n", encoding="utf-8")
    ballot_rel = str(ballot.relative_to(tmp_path))
    _write_classification_tsv(tmp_path)
    _write_run_jsonl(tmp_path)

    with pytest.raises(calibration_replay.CalibrationReplayError, match="does not match finding_id"):
        calibration_replay.validate_manifest_row(
            _manifest_row(fixture_plan=plan_rel, fixture_ballot=ballot_rel),
            repo_root=tmp_path,
        )


def test_resolve_voter_path_rejects_parent_traversal(tmp_path: Path) -> None:
    review = tmp_path / "review"
    review.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret\n", encoding="utf-8")

    with pytest.raises(calibration_replay.CalibrationReplayError, match="must stay under review tmpdir"):
        calibration_replay._resolve_voter_path(raw_path="../outside.txt", ballot_parent=review)


def test_seed_prior_round_ledger_writes_classification_rows(tmp_path: Path) -> None:
    round_one = tmp_path / "larch-logs" / "implement" / TEST_RUN_ID / "round-1"
    round_one.mkdir(parents=True)
    (round_one / "findings-classification.tsv").write_text(
        "finding_id\tv2_vote\tv1_vote\tv3_vote\tvoting_result\tscope\n"
        "FINDING_9\tNO\tNO\tNO\trejected\tin_scope\n",
        encoding="utf-8",
    )
    _write_jsonl(
        tmp_path / "larch-logs" / "implement" / TEST_RUN_ID,
        [
            {
                "id": "FINDING_9",
                "round_num": "1",
                "category": "Prior finding",
                "prose_body": "### FINDING_9: Prior finding\n\n- **Concern**: issue in python/foo.py:12\n",
            }
        ],
    )
    ledger_root = tmp_path / "replay-row"
    ledger_root.mkdir()

    calibration_replay._seed_prior_round_ledger(
        ledger_root=ledger_root,
        repo_root=tmp_path,
        run_id=TEST_RUN_ID,
        round_num=2,
    )

    ledger = ledger_root / "findings-ledger.tsv"
    assert ledger.is_file()
    assert "FINDING_9" in ledger.read_text(encoding="utf-8")


def test_validate_manifest_row_rejects_fixture_plan_outside_plans_dir(tmp_path: Path) -> None:
    outside = tmp_path / "outside.plan.txt"
    outside.write_text("Plan body\n", encoding="utf-8")

    with pytest.raises(calibration_replay.CalibrationReplayError, match="fixture_plan must be under"):
        calibration_replay.validate_manifest_row(
            _manifest_row(fixture_plan="outside.plan.txt"),
            repo_root=tmp_path,
        )


def test_validate_manifest_row_rejects_invalid_run_id_shape(tmp_path: Path) -> None:
    plan_rel = _plan_rel(tmp_path)

    with pytest.raises(calibration_replay.CalibrationReplayError, match="UUID-shaped implement run id"):
        calibration_replay.validate_manifest_row(
            _manifest_row(fixture_plan=plan_rel, run_id="RUN"),
            repo_root=tmp_path,
        )


def test_validate_manifest_row_rejects_empty_fixture_diff_when_required(tmp_path: Path) -> None:
    plan_rel = _plan_rel(tmp_path)
    diff = _write_diff_fixture(tmp_path, "")
    diff_rel = str(diff.relative_to(tmp_path))
    ballots = _ballots_dir(tmp_path)
    ballot = ballots / "ballot.txt"
    ballot.write_text("### FINDING_1: frozen\n\nbody\n", encoding="utf-8")
    ballot_rel = str(ballot.relative_to(tmp_path))
    _write_classification_tsv(tmp_path)
    _write_run_jsonl(tmp_path)

    with pytest.raises(calibration_replay.CalibrationReplayError, match="fixture_diff is empty"):
        calibration_replay.validate_manifest_row(
            _manifest_row(
                fixture_plan=plan_rel,
                fixture_diff=diff_rel,
                diff_required="true",
                fixture_ballot=ballot_rel,
            ),
            repo_root=tmp_path,
        )


def test_reconstruct_prior_round_ledger_includes_vote_tally_and_file_line(tmp_path: Path) -> None:
    run_root = tmp_path / "larch-logs" / "implement" / TEST_RUN_ID
    round_one = run_root / "round-1"
    round_one.mkdir(parents=True)
    (round_one / "findings-classification.tsv").write_text(
        "finding_id\tv2_vote\tv1_vote\tv3_vote\tvoting_result\tscope\n"
        "FINDING_9\tYES\tYES\tNO\taccepted\tin_scope\n",
        encoding="utf-8",
    )
    _write_jsonl(
        run_root,
        [
            {
                "id": "FINDING_9",
                "round_num": "1",
                "category": "Ledger parity",
                "prose_body": (
                    "### FINDING_9: Ledger parity\n\n"
                    "- **Concern**: bug in python/calibration_replay.py:100\n"
                ),
            }
        ],
    )

    rounds = calibration_replay._reconstruct_prior_round_ledger(
        repo_root=tmp_path,
        run_id=TEST_RUN_ID,
        round_num=2,
    )

    assert len(rounds) == 1
    entries = rounds[0][1]
    assert entries[0]["vote_tally"] == "YES=2/3"
    assert entries[0]["file_line"] == "python/calibration_replay.py:100"
    assert entries[0]["reason"]


def test_rebuild_ballot_main_rejects_ballot_outside_ballots_dir(tmp_path: Path) -> None:
    outside = tmp_path / "outside.ballot.txt"
    outside.write_text("### FINDING_1: frozen\n\nbody\n", encoding="utf-8")
    run_root = tmp_path / "larch-logs" / "implement" / TEST_RUN_ID
    run_root.mkdir(parents=True)

    exit_code = calibration_replay.rebuild_ballot_main(
        [
            "--finding-id",
            "FINDING_1",
            "--run-root",
            str(run_root),
            "--round-num",
            "1",
            "--fixture-ballot",
            "outside.ballot.txt",
            "--repo-root",
            str(tmp_path),
        ]
    )

    assert exit_code == 1
