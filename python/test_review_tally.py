from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import review_test_support as rts
import voting

ROOT = rts.ROOT
CLI = rts.CLI

_CLASSIFICATION_HEADER = (
    "finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\t"
    "v1_quality\tv1_uncertain\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\t"
    "v2_uncertain\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain"
)

_CODE_REVIEW_CLASSIFICATION_HEADER = (
    "finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\t"
    "v1_quality\tv1_uncertain\tv1_tool\tv2_vote\tv2_correctness\tv2_severity\t"
    "v2_quality\tv2_uncertain\tv2_tool\tv3_vote\tv3_correctness\tv3_severity\t"
    "v3_quality\tv3_uncertain\tv3_tool"
)


def _write_classification_ballot(path: Path) -> None:
    _ = path.write_text(
        """### FINDING_1: In-scope concern
- **Reviewer(s)**: cursor-a-output.txt, codex-b-output.txt
- **Concern**: Real issue.
- **Suggested revision**: Fix it.

### OOS_1: Future concern
- **Reviewer**: cursor-oos-output.txt
- **Concern**: Future issue.
- **Suggested revision**: File it.
""",
        encoding="utf-8",
    )


def _tsv_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return {row["finding_id"]: row for row in csv.DictReader(fh, delimiter="\t")}


def _run_cli(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged["LARCH_QUIET_DISABLE"] = "1"
    if env:
        merged.update(env)
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        env=merged,
        text=True,
        capture_output=True,
        check=False,
    )


def run_review(
    *args: str,
    env: dict[str, str] | None = None,
    quiet_disable: bool = True,
) -> subprocess.CompletedProcess[str]:
    return rts.run_review(*args, env=env, quiet_disable=quiet_disable)


def _prepare_neutralized_ballot(tmp_path: Path, attributed_text: str) -> tuple[Path, Path]:
    attributed = tmp_path / "attributed.md"
    _ = attributed.write_text(attributed_text, encoding="utf-8")
    ballot = tmp_path / "ballot.md"
    _ = ballot.write_text(attributed_text, encoding="utf-8")
    map_file = tmp_path / "proposer-map.tsv"
    voting.write_proposer_map(ballot, map_file)
    _ = ballot.write_text(voting.neutralize_reviewer_attribution(attributed_text), encoding="utf-8")
    return ballot, map_file


def _mk_ballot(path: Path) -> None:
    _ = path.write_text(
        """### FINDING_1: First in-scope finding
- **Reviewer**: Codex-Structure
- **Concern**: Concern 1.
- **Suggested revision**: Revision 1.

### FINDING_2: Second in-scope finding
- **Reviewer**: Cursor-Security
- **Concern**: Concern 2.
- **Suggested revision**: Revision 2.

### FINDING_3: [OUT_OF_SCOPE] OOS observation
- **Reviewer**: Codex-Plan-fidelity
- **Concern**: Pre-existing thing.
- **Suggested revision**: Revision 3.
""",
        encoding="utf-8",
    )


def test_emit_tally_writes_summary_json(tmp_path: Path) -> None:
    tally = tmp_path / "review-tally.env"
    _ = tally.write_text("ACCEPTED_COUNT=0\nREJECTED_COUNT=0\nNEUTRAL_COUNT=0\n", encoding="utf-8")
    accepted = tmp_path / "accepted-findings.md"
    _ = accepted.write_text("", encoding="utf-8")
    oos = tmp_path / "oos.md"
    _ = oos.write_text("", encoding="utf-8")

    result = run_review(
        "emit-tally",
        "--tally-file",
        str(tally),
        "--accepted-findings-file",
        str(accepted),
        "--oos-file",
        str(oos),
        "--review-tmpdir",
        str(tmp_path),
        "--round",
        "1",
        "--mode",
        "description",
    )

    assert result.returncode == 0, result.stderr
    assert "REVIEW_SUMMARY_FILE=" in result.stdout
    assert (tmp_path / "review-summary.json").exists()


def test_log_phase_rejects_unknown_batch(tmp_path: Path) -> None:
    payload = tmp_path / "payload.txt"
    _ = payload.write_text("payload\n", encoding="utf-8")

    result = run_review(
        "log-phase",
        "--run-id",
        "run-1",
        "--batch",
        "unknown",
        "--action",
        "write",
        "--payload-file",
        str(payload),
        "--log-root",
        str(tmp_path / "logs"),
    )

    assert result.returncode == 2
    assert "unregistered review batch" in result.stderr


def test_tally_three_voter_mixed_outcomes(tmp_path: Path) -> None:
    case = tmp_path / "case1"
    case.mkdir()
    _mk_ballot(case / "ballot.md")
    _ = (case / "cursor-vote-output.txt").write_text(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n"
        "FINDING_2: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n"
        "FINDING_3: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n",
        encoding="utf-8",
    )
    _ = (case / "codex-vote-output.txt").write_text(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n"
        "FINDING_2: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n"
        "FINDING_3: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n",
        encoding="utf-8",
    )
    _ = (case / "claude-vote-output.txt").write_text(
        "FINDING_1: NO CORRECTNESS=partially-true SEVERITY=minor QUALITY=weak UNCERTAIN=false\n"
        "FINDING_2: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n"
        "FINDING_3: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n",
        encoding="utf-8",
    )

    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--voter-files",
        str(case / "cursor-vote-output.txt"),
        str(case / "codex-vote-output.txt"),
        str(case / "claude-vote-output.txt"),
        "--review-tmpdir",
        str(case),
    )

    assert result.returncode == 0, result.stderr
    assert rts.kv_get(result.stdout, "ACCEPTED_COUNT") == "1"
    assert rts.kv_get(result.stdout, "REJECTED_COUNT") == "1"
    assert rts.kv_get(result.stdout, "OOS_ACCEPTED_COUNT") == "1"
    assert "FINDING_1: First in-scope finding" in (case / "accepted-findings.md").read_text(encoding="utf-8")
    assert "FINDING_2" in (case / "rejected-findings.md").read_text(encoding="utf-8")


def test_tally_excludes_narrative_only_voter_parse_rate_check(tmp_path: Path) -> None:
    case = tmp_path / "narrative-voter"
    case.mkdir()
    _mk_ballot(case / "ballot.md")
    _ = (case / "cursor-vote-output.txt").write_text(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n"
        "FINDING_2: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n"
        "FINDING_3: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n",
        encoding="utf-8",
    )
    _ = (case / "codex-vote-output.txt").write_text(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n"
        "FINDING_2: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n"
        "FINDING_3: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n",
        encoding="utf-8",
    )
    _ = (case / "claude-vote-output.txt").write_text("narrative only\n", encoding="utf-8")

    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--voter-files",
        str(case / "cursor-vote-output.txt"),
        str(case / "codex-vote-output.txt"),
        str(case / "claude-vote-output.txt"),
        "--review-tmpdir",
        str(case),
    )

    assert result.returncode == 0, result.stderr
    assert rts.kv_get(result.stdout, "ELIGIBLE_VOTER_COUNT") == "3"
    assert rts.kv_get(result.stdout, "VOTER_COUNT") == "2"
    assert rts.kv_get(result.stdout, "TALLY_STATUS") == "ok"
    tally = (case / "voting-tally.md").read_text(encoding="utf-8")
    assert "narrative-only output" in tally
    assert "parse-rate" in tally


def test_tally_security_oos_holdback(tmp_path: Path) -> None:
    case = tmp_path / "security-oos"
    case.mkdir()
    _ = (case / "ballot.md").write_text(
        """### FINDING_1: [OUT_OF_SCOPE] security Privilege escalation in setup
- **Reviewer**: Codex-Security
- **focus-area**: security
- **Concern**: This is sensitive.
- **Suggested revision**: redacted.
""",
        encoding="utf-8",
    )
    for name in ("cursor-vote-output.txt", "codex-vote-output.txt", "claude-vote-output.txt"):
        _ = (case / name).write_text("FINDING_1: YES\n", encoding="utf-8")

    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--voter-files",
        str(case / "cursor-vote-output.txt"),
        str(case / "codex-vote-output.txt"),
        str(case / "claude-vote-output.txt"),
        "--review-tmpdir",
        str(case),
    )

    assert result.returncode == 0, result.stderr
    assert rts.kv_get(result.stdout, "OOS_ACCEPTED_COUNT") == "0"
    assert not (case / "oos-accepted-review.md").read_text(encoding="utf-8").strip()


def test_tally_scope_fit_drift_reclassifies_out_of_diff(tmp_path: Path) -> None:
    case = tmp_path / "scope-drift"
    case.mkdir()
    _ = (case / "ballot.md").write_text(
        """### FINDING_1: **Important** — `code-quality` — `docs/linting.md:22`
- **Reviewer**: Cursor-Correctness
- **Concern**: Usage CI bullet still documents harnesses-1 through harnesses-10 after eleven-way sharding.
- **Suggested revision**: Update to reflect 11 shards.

### FINDING_2: **Important** — `correctness` — `python/cli.py:42`
- **Reviewer**: Codex-Structure
- **Concern**: Null check missing on return path.
- **Suggested revision**: Add nil guard.
""",
        encoding="utf-8",
    )
    _ = (case / "scope-files.txt").write_text("python/cli.py\n", encoding="utf-8")
    for name in ("cursor-vote-output.txt", "codex-vote-output.txt", "claude-vote-output.txt"):
        _ = (case / name).write_text("FINDING_1: YES\nFINDING_2: YES\n", encoding="utf-8")

    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--voter-files",
        str(case / "cursor-vote-output.txt"),
        str(case / "codex-vote-output.txt"),
        str(case / "claude-vote-output.txt"),
        "--scope-files",
        str(case / "scope-files.txt"),
        "--review-tmpdir",
        str(case),
    )

    assert result.returncode == 0, result.stderr
    assert rts.kv_get(result.stdout, "OUT_OF_SCOPE_DRIFT_COUNT") == "1"
    assert rts.kv_get(result.stdout, "ACCEPTED_COUNT") == "1"
    accepted = (case / "accepted-findings.md").read_text(encoding="utf-8")
    assert "docs/linting.md" not in accepted
    assert "docs/linting.md" in (case / "oos.md").read_text(encoding="utf-8")


def test_tally_plan_file_scope_fit_exemption(tmp_path: Path) -> None:
    case = tmp_path / "plan-exempt"
    case.mkdir()
    _ = (case / "ballot.md").write_text(
        """### FINDING_1: **Important** — `code-quality` — `docs/linting.md:22`
- **Reviewer**: Cursor-Correctness
- **Concern**: Stale shard reference.
- **Suggested revision**: Update.
""",
        encoding="utf-8",
    )
    _ = (case / "scope-files.txt").write_text("python/cli.py\n", encoding="utf-8")
    _ = (case / "plan.txt").write_text("Touch docs/linting.md per plan section 3.\n", encoding="utf-8")
    for name in ("cursor-vote-output.txt", "codex-vote-output.txt", "claude-vote-output.txt"):
        _ = (case / name).write_text("FINDING_1: YES\n", encoding="utf-8")

    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--voter-files",
        str(case / "cursor-vote-output.txt"),
        str(case / "codex-vote-output.txt"),
        str(case / "claude-vote-output.txt"),
        "--scope-files",
        str(case / "scope-files.txt"),
        "--plan-file",
        str(case / "plan.txt"),
        "--review-tmpdir",
        str(case),
    )

    assert result.returncode == 0, result.stderr
    assert rts.kv_get(result.stdout, "OUT_OF_SCOPE_DRIFT_COUNT") == "0"
    assert rts.kv_get(result.stdout, "ACCEPTED_COUNT") == "1"
    assert "docs/linting.md" in (case / "accepted-findings.md").read_text(encoding="utf-8")


def test_emit_tally_preserves_existing_oos_accepted_sink(tmp_path: Path) -> None:
    case = tmp_path / "preserve-oos"
    case.mkdir()
    tally = case / "tally.env"
    _ = tally.write_text("ACCEPTED_COUNT=0\nREJECTED_COUNT=0\nOOS_ACCEPTED_COUNT=1\n", encoding="utf-8")
    accepted = case / "accepted.md"
    _ = accepted.write_text("", encoding="utf-8")
    oos = case / "oos.md"
    _ = oos.write_text(
        """### OOS_1: [OUT_OF_SCOPE] preserved observation
- **Reviewer**: stub
- **Concern**: keep me
""",
        encoding="utf-8",
    )
    sink = case / "oos-accepted-review.md"
    preserved = "### OOS_1: [OUT_OF_SCOPE] tally-written preserved sink\n"
    _ = sink.write_text(preserved, encoding="utf-8")

    result = run_review(
        "emit-tally",
        "--tally-file",
        str(tally),
        "--accepted-findings-file",
        str(accepted),
        "--oos-file",
        str(oos),
        "--review-tmpdir",
        str(case),
        "--round",
        "1",
        "--mode",
        "description",
    )

    assert result.returncode == 0, result.stderr
    assert sink.read_text(encoding="utf-8") == preserved


def test_tally_zero_voters_main_agent_vote_required(tmp_path: Path) -> None:
    case = tmp_path / "zero-voters"
    case.mkdir()
    _mk_ballot(case / "ballot.md")

    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--review-tmpdir",
        str(case),
    )

    assert result.returncode == 0, result.stderr
    assert rts.kv_get(result.stdout, "TALLY_STATUS") == "main-agent-vote-required"
    assert rts.kv_get(result.stdout, "VOTER_COUNT") == "0"


def test_tally_security_classifier_failure_fails_closed(tmp_path: Path) -> None:
    case = tmp_path / "security-classifier-fail"
    case.mkdir()
    bin_dir = case / "bin"
    bin_dir.mkdir()
    rts.write_executable(
        bin_dir / "python3",
        """#!/usr/bin/env bash
exit 1
""",
    )
    _ = (case / "ballot.md").write_text(
        """### FINDING_1: [OUT_OF_SCOPE] security follow-up
- **Reviewer**: Cursor-Security
- **Concern**: focus-area = security
- **Suggested revision**: Hold locally.
""",
        encoding="utf-8",
    )
    _ = (case / "cursor-vote-output.txt").write_text("FINDING_1: YES\n", encoding="utf-8")
    _ = (case / "codex-vote-output.txt").write_text("FINDING_1: YES\n", encoding="utf-8")

    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--voter-files",
        str(case / "cursor-vote-output.txt"),
        str(case / "codex-vote-output.txt"),
        "--review-tmpdir",
        str(case),
        env={"PATH": f"{bin_dir}:{os.environ.get('PATH', '')}"},
    )

    assert result.returncode == 2
    assert not (case / "oos-accepted-review.md").read_text(encoding="utf-8").strip()


def test_findings_classification_nested_impl_path_and_write_round(tmp_path: Path) -> None:
    impl_parent = tmp_path / "impl-parent"
    round_dir = impl_parent / "round-1"
    round_dir.mkdir(parents=True)
    _write_classification_ballot(round_dir / "ballot.md")
    _ = (round_dir / "v1.txt").write_text(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n"
        "OOS_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n",
        encoding="utf-8",
    )
    _ = (round_dir / "v2.txt").write_text(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=adequate UNCERTAIN=false\n"
        "OOS_1: NO CORRECTNESS=partially-true SEVERITY=minor QUALITY=weak UNCERTAIN=false\n",
        encoding="utf-8",
    )
    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(round_dir / "ballot.md"),
        "--review-tmpdir",
        str(round_dir),
        "--session-env-path",
        str(impl_parent / "session-env.sh"),
        "--voter-files",
        str(round_dir / "v1.txt"),
        str(round_dir / "v2.txt"),
        env={"IMPLEMENT_TMPDIR": str(impl_parent)},
    )
    assert result.returncode == 0, result.stderr
    class_file = Path(rts.kv_get(result.stdout, "FINDINGS_CLASSIFICATION_TSV_FILE") or "")
    assert class_file == round_dir / "findings-classification.tsv"
    header = class_file.read_text(encoding="utf-8").splitlines()[0]
    assert header == _CLASSIFICATION_HEADER
    rows = _tsv_rows(class_file)
    finding = rows["FINDING_1"]
    assert finding["voting_result"] == "accepted"
    assert finding["reviewer_slots"] == "cursor-a-output.txt|codex-b-output.txt"
    assert finding["v1_vote"] == "YES"
    assert finding["v2_vote"] == "YES"
    assert rows["OOS_1"]["voting_result"] == "neutral"
    log_root = tmp_path / "logs"
    write_round = _run_cli(
        "run-log",
        "write-round",
        "--log-root",
        str(log_root),
        "--skill",
        "implement",
        "--run-id",
        "run-a",
        "--round",
        "1",
        "--source-dir",
        str(round_dir),
    )
    assert write_round.returncode == 0, write_round.stderr
    assert (log_root / "implement" / "run-a" / "round-1" / "findings-classification.tsv").is_file()


def test_findings_classification_standalone_lenient_missing_rating(tmp_path: Path) -> None:
    case = tmp_path / "b"
    case.mkdir()
    _write_classification_ballot(case / "ballot.md")
    _ = (case / "v1.txt").write_text(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n"
        "OOS_1: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n",
        encoding="utf-8",
    )
    _ = (case / "v2.txt").write_text(
        "FINDING_1: YES SEVERITY=major QUALITY=adequate UNCERTAIN=false\n"
        "OOS_1: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n",
        encoding="utf-8",
    )
    _ = (case / "v3.txt").write_text(
        "FINDING_1: NO CORRECTNESS=partially-true SEVERITY=minor QUALITY=weak UNCERTAIN=false\n"
        "OOS_1: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n",
        encoding="utf-8",
    )
    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--review-tmpdir",
        str(case),
        "--round-num",
        "1",
        "--voter-files",
        str(case / "v1.txt"),
        str(case / "v2.txt"),
        str(case / "v3.txt"),
        env={"IMPLEMENT_TMPDIR": ""},
    )
    assert result.returncode == 0, result.stderr
    class_file = Path(rts.kv_get(result.stdout, "FINDINGS_CLASSIFICATION_TSV_FILE") or "")
    assert class_file == case / "findings-classification-round-1.tsv"
    row = _tsv_rows(class_file)["FINDING_1"]
    assert row["voting_result"] == "accepted"
    assert row["v2_vote"] == "YES"
    assert row["v2_correctness"] == ""
    assert row["v2_uncertain"] == "true"


def test_findings_classification_standalone_session_env_round_scoped(tmp_path: Path) -> None:
    case = tmp_path / "b2"
    case.mkdir()
    ambient = tmp_path / "ambient-impl"
    ambient.mkdir()
    _write_classification_ballot(case / "ballot.md")
    _ = (case / "v1.txt").write_text(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n"
        "OOS_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n",
        encoding="utf-8",
    )
    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--review-tmpdir",
        str(case),
        "--session-env-path",
        str(case / "session-env.sh"),
        "--round-num",
        "2",
        "--voter-files",
        str(case / "v1.txt"),
        env={"IMPLEMENT_TMPDIR": str(ambient)},
    )
    assert result.returncode == 0, result.stderr
    class_file = Path(rts.kv_get(result.stdout, "FINDINGS_CLASSIFICATION_TSV_FILE") or "")
    assert class_file == case / "findings-classification-round-2.tsv"


def test_findings_classification_standalone_round_n_suffix(tmp_path: Path) -> None:
    case = tmp_path / "impl-shape" / "round-3"
    case.mkdir(parents=True)
    _write_classification_ballot(case / "ballot.md")
    _ = (case / "v1.txt").write_text(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n"
        "OOS_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n",
        encoding="utf-8",
    )
    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--review-tmpdir",
        str(case),
        "--round-num",
        "3",
        "--voter-files",
        str(case / "v1.txt"),
        env={"IMPLEMENT_TMPDIR": ""},
    )
    assert result.returncode == 0, result.stderr
    class_file = Path(rts.kv_get(result.stdout, "FINDINGS_CLASSIFICATION_TSV_FILE") or "")
    assert class_file == case / "findings-classification-round-3.tsv"


def test_findings_classification_zero_voters_tsv_rejected_rows(tmp_path: Path) -> None:
    case = tmp_path / "c"
    case.mkdir()
    _write_classification_ballot(case / "ballot.md")
    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--review-tmpdir",
        str(case),
        env={"IMPLEMENT_TMPDIR": ""},
    )
    assert result.returncode == 0, result.stderr
    assert rts.kv_get(result.stdout, "TALLY_STATUS") == "main-agent-vote-required"
    class_file = Path(rts.kv_get(result.stdout, "FINDINGS_CLASSIFICATION_TSV_FILE") or "")
    rows = list(csv.DictReader(class_file.read_text(encoding="utf-8").splitlines(), delimiter="\t"))
    assert len(rows) == 2
    for row in rows:
        assert row["voting_result"] == "rejected"
        for key, value in row.items():
            if len(key) > 2 and key[0] == "v" and key[1].isdigit() and key[2] == "_":
                assert value == ""


def test_findings_classification_empty_ballot_header_only(tmp_path: Path) -> None:
    case = tmp_path / "d"
    case.mkdir()
    _ = (case / "ballot.md").write_text("", encoding="utf-8")
    _ = (case / "v1.txt").write_text(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n",
        encoding="utf-8",
    )
    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--review-tmpdir",
        str(case),
        "--voter-files",
        str(case / "v1.txt"),
        env={"IMPLEMENT_TMPDIR": ""},
    )
    assert result.returncode == 0, result.stderr
    class_file = Path(rts.kv_get(result.stdout, "FINDINGS_CLASSIFICATION_TSV_FILE") or "")
    assert class_file.is_file()
    assert len(class_file.read_text(encoding="utf-8").splitlines()) == 1


def test_findings_classification_multi_round_log_batches(tmp_path: Path) -> None:
    case = tmp_path / "e"
    case.mkdir()
    _write_classification_ballot(case / "ballot.md")
    _ = (case / "v1.txt").write_text(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n"
        "OOS_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n",
        encoding="utf-8",
    )
    log_root = case / "logs"
    for round_num in (1, 2):
        result = run_review(
            "tally-code-votes",
            "--ballot-file",
            str(case / "ballot.md"),
            "--review-tmpdir",
            str(case),
            "--round-num",
            str(round_num),
            "--voter-files",
            str(case / "v1.txt"),
            env={"IMPLEMENT_TMPDIR": ""},
        )
        assert result.returncode == 0, result.stderr
        class_file = Path(rts.kv_get(result.stdout, "FINDINGS_CLASSIFICATION_TSV_FILE") or "")
        assert class_file == case / f"findings-classification-round-{round_num}.tsv"
        log_result = run_review(
            "log-phase",
            "--log-root",
            str(log_root),
            "--run-id",
            "run-e",
            "--batch",
            f"review-findings-classification-round-{round_num}",
            "--action",
            "write",
            "--payload-file",
            str(class_file),
        )
        assert log_result.returncode == 0, log_result.stderr
        published = log_root / "review" / "run-e" / f"review-findings-classification-round-{round_num}.tsv"
        assert published.is_file()


def test_findings_classification_parser_vote_for_id_parity(tmp_path: Path) -> None:
    votes = tmp_path / "votes.txt"
    _ = votes.write_text(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n"
        "OOS_1: NO CORRECTNESS=partially-true SEVERITY=minor QUALITY=weak UNCERTAIN=false\n",
        encoding="utf-8",
    )
    for finding_id in ("FINDING_1", "OOS_1"):
        parsed = _run_cli("voting", "parse-judge-vote", str(votes), finding_id)
        assert parsed.returncode == 0, parsed.stderr
        parser_vote = rts.kv_get(parsed.stdout, "PARSED_VOTE")
        lib = _run_cli("voting", "vote-for-id", finding_id, str(votes))
        assert lib.returncode == 0, lib.stderr
        assert parser_vote == lib.stdout.strip()
    missing = _run_cli("voting", "parse-judge-vote", str(votes), "FINDING_2")
    assert rts.kv_get(missing.stdout, "PARSED_VOTE") == ""


def test_findings_classification_judge_error_in_tsv(tmp_path: Path) -> None:
    case = tmp_path / "f2"
    case.mkdir()
    _write_classification_ballot(case / "ballot.md")
    _ = (case / "v1.txt").write_text(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n"
        "OOS_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n",
        encoding="utf-8",
    )
    _ = (case / "v2.txt").write_text(
        "OOS_1: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n",
        encoding="utf-8",
    )
    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--review-tmpdir",
        str(case),
        "--round-num",
        "1",
        "--voter-files",
        str(case / "v1.txt"),
        str(case / "v2.txt"),
        env={"IMPLEMENT_TMPDIR": ""},
    )
    assert result.returncode == 0, result.stderr
    row = _tsv_rows(Path(rts.kv_get(result.stdout, "FINDINGS_CLASSIFICATION_TSV_FILE") or ""))["FINDING_1"]
    assert row["voting_result"] == "neutral"
    assert row["v2_vote"] == "JUDGE_ERROR"
    assert row["v2_correctness"] == ""
    assert row["v2_severity"] == ""
    assert row["v2_quality"] == ""
    assert row["v2_uncertain"] == "true"


def test_findings_classification_formula_neutralized_reviewer(tmp_path: Path) -> None:
    case = tmp_path / "f3"
    case.mkdir()
    _ = (case / "ballot.md").write_text(
        """### FINDING_1: Spreadsheet payload
- **Reviewer**: =SUM(1,1)
- **Concern**: Real issue.
- **Suggested revision**: Fix it.
""",
        encoding="utf-8",
    )
    _ = (case / "v1.txt").write_text(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n",
        encoding="utf-8",
    )
    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--review-tmpdir",
        str(case),
        "--round-num",
        "1",
        "--voter-files",
        str(case / "v1.txt"),
        env={"IMPLEMENT_TMPDIR": ""},
    )
    assert result.returncode == 0, result.stderr
    row = _tsv_rows(Path(rts.kv_get(result.stdout, "FINDINGS_CLASSIFICATION_TSV_FILE") or ""))["FINDING_1"]
    assert row["reviewer_slots"] == "'=SUM(1|1)"


def test_findings_classification_enum_sanitization(tmp_path: Path) -> None:
    case = tmp_path / "g"
    case.mkdir()
    _write_classification_ballot(case / "ballot.md")
    _ = (case / "v1.txt").write_text(
        "FINDING_1: YES CORRECTNESS=true|owned SEVERITY=critical QUALITY=great UNCERTAIN=maybe\n"
        "OOS_1: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n",
        encoding="utf-8",
    )
    _ = (case / "v2.txt").write_text(
        "FINDING_1: NO CORRECTNESS=partially-true SEVERITY=minor QUALITY=weak UNCERTAIN=false\n"
        "OOS_1: NO CORRECTNESS=partially-true SEVERITY=minor QUALITY=weak UNCERTAIN=false\n",
        encoding="utf-8",
    )
    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--review-tmpdir",
        str(case),
        "--round-num",
        "1",
        "--voter-files",
        str(case / "v1.txt"),
        str(case / "v2.txt"),
        env={"IMPLEMENT_TMPDIR": ""},
    )
    assert result.returncode == 0, result.stderr
    allowed = {
        "voting_result": {"accepted", "neutral", "rejected"},
        "vote": {"", "YES", "NO", "JUDGE_ERROR"},
        "correctness": {"", "true", "partially-true", "false-positive", "uncertain"},
        "severity": {"", "blocker", "major", "minor", "nit", "uncertain"},
        "quality": {"", "excellent", "good", "adequate", "weak", "no-fix", "uncertain"},
        "uncertain": {"", "true", "false"},
    }
    for row in _tsv_rows(Path(rts.kv_get(result.stdout, "FINDINGS_CLASSIFICATION_TSV_FILE") or "")).values():
        assert row["voting_result"] in allowed["voting_result"]
        for idx in (1, 2, 3):
            assert row[f"v{idx}_vote"] in allowed["vote"]
            assert row[f"v{idx}_correctness"] in allowed["correctness"]
            assert row[f"v{idx}_severity"] in allowed["severity"]
            assert row[f"v{idx}_quality"] in allowed["quality"]
            assert row[f"v{idx}_uncertain"] in allowed["uncertain"]


def test_findings_classification_quiet_mode_emits_tsv(tmp_path: Path) -> None:
    case = tmp_path / "h"
    case.mkdir()
    _write_classification_ballot(case / "ballot.md")
    _ = (case / "v1.txt").write_text(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n"
        "OOS_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n",
        encoding="utf-8",
    )
    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--review-tmpdir",
        str(case),
        "--round-num",
        "1",
        "--voter-files",
        str(case / "v1.txt"),
        env={"IMPLEMENT_TMPDIR": ""},
        quiet_disable=False,
    )
    assert result.returncode == 0, result.stderr
    class_file = Path(rts.kv_get(result.stdout, "FINDINGS_CLASSIFICATION_TSV_FILE") or "")
    assert class_file.is_file()
    assert class_file.stat().st_size > 0


def test_tally_three_slot_failed_middle_preserves_slot_columns(tmp_path: Path) -> None:
    case = tmp_path / "three-slot-middle"
    case.mkdir()
    _mk_ballot(case / "ballot.md")
    _ = (case / "v1.txt").write_text("FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n", encoding="utf-8")
    _ = (case / "v2.txt").write_text("", encoding="utf-8")
    _ = (case / "v3.txt").write_text("FINDING_1: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n", encoding="utf-8")

    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--review-tmpdir",
        str(case),
        "--cursor-available",
        "true",
        "--codex-available",
        "false",
        "--voter-files",
        str(case / "v1.txt"),
        "",
        str(case / "v3.txt"),
        "--voter-tools",
        "cursor-validity",
        "cursor-plan-fidelity",
        "cursor-pragmatism",
        env={"CLAUDE_PLUGIN_ROOT": str(ROOT)},
    )

    assert result.returncode == 0, result.stderr
    assert rts.kv_get(result.stdout, "ELIGIBLE_VOTER_COUNT") == "2"
    class_file = Path(rts.kv_get(result.stdout, "FINDINGS_CLASSIFICATION_TSV_FILE") or "")
    lines = class_file.read_text(encoding="utf-8").splitlines()
    assert lines[0] == _CODE_REVIEW_CLASSIFICATION_HEADER
    assert all(len(line.split("\t")) == 21 for line in lines)
    row = _tsv_rows(class_file)["FINDING_1"]
    assert row["v1_tool"] == "cursor-validity"
    assert row["v2_vote"] == ""
    assert row["v2_tool"] == "cursor-plan-fidelity"
    assert row["v3_vote"] == "NO"
    assert row["v3_tool"] == "cursor-pragmatism"


def test_tally_three_slot_mismatched_tools_fails(tmp_path: Path) -> None:
    case = tmp_path / "three-slot-mismatch"
    case.mkdir()
    _mk_ballot(case / "ballot.md")
    _ = (case / "v1.txt").write_text("FINDING_1: YES\n", encoding="utf-8")
    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--review-tmpdir",
        str(case),
        "--voter-files",
        str(case / "v1.txt"),
        "--voter-tools",
        "cursor-validity",
    )
    assert result.returncode == 2


def test_tally_three_slot_claude_fallback_single_quorum(tmp_path: Path) -> None:
    case = tmp_path / "claude-fallback"
    case.mkdir()
    _mk_ballot(case / "ballot.md")
    _ = (case / "claude.txt").write_text("FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n", encoding="utf-8")
    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--review-tmpdir",
        str(case),
        "--cursor-available",
        "false",
        "--codex-available",
        "true",
        "--voter-files",
        str(case / "claude.txt"),
        "",
        "",
        "--voter-tools",
        "claude",
        "cursor-plan-fidelity",
        "cursor-pragmatism",
        env={"CLAUDE_PLUGIN_ROOT": str(ROOT)},
    )
    assert result.returncode == 0, result.stderr
    assert rts.kv_get(result.stdout, "VOTER_COUNT") == "1"
    row = _tsv_rows(Path(rts.kv_get(result.stdout, "FINDINGS_CLASSIFICATION_TSV_FILE") or ""))["FINDING_1"]
    assert row["voting_result"] == "accepted"
    assert row["v1_tool"] == "claude"
    assert row["v2_tool"] == "cursor-plan-fidelity"
    assert row["v3_tool"] == "cursor-pragmatism"


def test_emit_tally_refuses_destructive_oos_rebuild_mismatch(tmp_path: Path) -> None:
    case = tmp_path / "oos-mismatch"
    case.mkdir()
    tally = case / "tally.env"
    _ = tally.write_text("ACCEPTED_COUNT=0\nREJECTED_COUNT=0\nOOS_ACCEPTED_COUNT=2\n", encoding="utf-8")
    accepted = case / "accepted.md"
    _ = accepted.write_text("", encoding="utf-8")
    oos = case / "oos.md"
    _ = oos.write_text("", encoding="utf-8")
    _ = (case / "oos-accepted-review.md").write_text("### OOS_1: Existing\n- **Concern**: keep\n", encoding="utf-8")

    result = run_review(
        "emit-tally",
        "--tally-file",
        str(tally),
        "--accepted-findings-file",
        str(accepted),
        "--oos-file",
        str(oos),
        "--review-tmpdir",
        str(case),
        "--round",
        "1",
        "--mode",
        "description",
    )

    assert result.returncode == 1
    assert "refusing destructive rebuild" in result.stderr


def test_emit_tally_fallback_counts_legacy_rows(tmp_path: Path) -> None:
    case = tmp_path / "legacy-tally"
    case.mkdir()
    tally = case / "review-tally.env"
    _ = tally.write_text(
        "FINDING_1_ACCEPTED=true\nFINDING_1_OUTCOME=accepted\n"
        "FINDING_2_ACCEPTED=false\nFINDING_2_OUTCOME=rejected\nFINDING_2_REJECTED_SUBTYPE=true_rejected\n",
        encoding="utf-8",
    )
    accepted = case / "accepted-findings.md"
    _ = accepted.write_text("### FINDING_1: kept\n", encoding="utf-8")
    oos = case / "oos.md"
    _ = oos.write_text("", encoding="utf-8")

    result = run_review(
        "emit-tally",
        "--tally-file",
        str(tally),
        "--accepted-findings-file",
        str(accepted),
        "--oos-file",
        str(oos),
        "--review-tmpdir",
        str(case),
        "--round",
        "1",
        "--mode",
        "description",
    )

    assert result.returncode == 0, result.stderr
    summary = json.loads((case / "review-summary.json").read_text(encoding="utf-8"))
    assert summary["accepted_count"] == 1
    assert summary["rejected_count"] == 1
    assert "1 accepted, 1 rejected" in (case / "review-round-summary.md").read_text(encoding="utf-8")


def test_tally_not_substantive_warning_in_voting_tally(tmp_path: Path) -> None:
    case = tmp_path / "not-substantive"
    case.mkdir()
    _mk_ballot(case / "ballot.md")
    _ = (case / "cursor-vote-output.txt").write_text("FINDING_1: YES\nFINDING_2: YES\nFINDING_3: YES\n", encoding="utf-8")

    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--voter-files",
        str(case / "cursor-vote-output.txt"),
        "--review-tmpdir",
        str(case),
        "--not-substantive-count",
        "2",
    )

    assert result.returncode == 0, result.stderr
    tally = (case / "voting-tally.md").read_text(encoding="utf-8")
    assert "NOT_SUBSTANTIVE" in tally


def test_tally_manifest_yield_and_dead_scoreboard_rows(tmp_path: Path) -> None:
    case = tmp_path / "manifest-yield"
    case.mkdir()
    _ = (case / "ballot.md").write_text(
        """### FINDING_1: In-scope issue
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: real bug
- **Suggested revision**: fix it
""",
        encoding="utf-8",
    )
    _ = (case / "cursor-specialist-correctness-output.txt").write_text("FINDING_1: YES\n", encoding="utf-8")
    dead = case / "cursor-specialist-testing-output.txt"
    _ = dead.write_text("narrative only\n", encoding="utf-8")
    manifest = case / "panel.ndjson"
    _ = manifest.write_text(
        '{"slot":"correctness","tool":"cursor","output":"'
        + str(case / "cursor-specialist-correctness-output.txt")
        + '","focus_area":"correctness","weight":1}\n'
        '{"slot":"testing","tool":"cursor","output":"'
        + str(dead)
        + '","focus_area":"risk-integration","weight":1}\n',
        encoding="utf-8",
    )
    _ = (case / "collector-results.env").write_text(
        f"REVIEWER_FILE={dead}\nSTATUS=NOT_SUBSTANTIVE\n\n",
        encoding="utf-8",
    )

    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--voter-files",
        str(case / "cursor-specialist-correctness-output.txt"),
        "--review-tmpdir",
        str(case),
        "--manifest-file",
        str(manifest),
        "--collector-results-file",
        str(case / "collector-results.env"),
    )

    assert result.returncode == 0, result.stderr
    assert rts.kv_get(result.stdout, "YIELD_TSV_FILE")
    yield_rows = list(csv.DictReader((case / "scout-archetype-yield.tsv").open(encoding="utf-8"), delimiter="\t"))
    assert len(yield_rows) == 2
    correctness = next(row for row in yield_rows if row["archetype_name"] == "correctness")
    assert correctness["findings_total"] == "1"
    assert correctness["findings_accepted"] == "1"
    tally = (case / "voting-tally.md").read_text(encoding="utf-8")
    assert "cursor-specialist-testing" in tally
    assert "STATUS=NOT_SUBSTANTIVE" in tally


def test_tally_oos_seq_seeded_from_accumulated_oos(tmp_path: Path) -> None:
    parent = tmp_path / "impl-parent"
    round_dir = parent / "round-2"
    round_dir.mkdir(parents=True)
    _ = (parent / "accumulated-oos.md").write_text(
        """### OOS_1: [OUT_OF_SCOPE] prior round
- **Reviewer**: prior.txt
- **Concern**: already filed
""",
        encoding="utf-8",
    )
    _ = (round_dir / "ballot.md").write_text(
        """### OOS_1: [OUT_OF_SCOPE] new accepted
- **Reviewer**: cursor-oos-output.txt
- **Concern**: new follow-up
""",
        encoding="utf-8",
    )
    _ = (round_dir / "cursor-oos-output.txt").write_text("OOS_1: YES\n", encoding="utf-8")

    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(round_dir / "ballot.md"),
        "--review-tmpdir",
        str(round_dir),
        "--session-env-path",
        str(parent / "session-env.sh"),
        "--voter-files",
        str(round_dir / "cursor-oos-output.txt"),
    )

    assert result.returncode == 0, result.stderr
    accepted = (round_dir / "oos-accepted-review.md").read_text(encoding="utf-8")
    assert "### OOS_2:" in accepted
    assert "### OOS_1:" not in accepted


def test_neutralized_ballot_sidecar_preserves_reviewer_slots(tmp_path: Path) -> None:
    attributed = """### FINDING_1: First in-scope finding
- **Reviewer**: Codex-Structure
- **Concern**: Concern 1.
- **Suggested revision**: Revision 1.
"""
    case = tmp_path / "neutral-sidecar"
    case.mkdir()
    ballot, map_file = _prepare_neutralized_ballot(case, attributed)
    attr_ballot = case / "attr.md"
    _ = attr_ballot.write_text(attributed, encoding="utf-8")
    voter = case / "v1.txt"
    _ = voter.write_text(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n",
        encoding="utf-8",
    )
    result_attr = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(attr_ballot),
        "--review-tmpdir",
        str(case / "attr"),
        "--round-num",
        "1",
        "--voter-files",
        str(voter),
        env={"IMPLEMENT_TMPDIR": ""},
    )
    result_neutral = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(ballot),
        "--review-tmpdir",
        str(case / "neutral"),
        "--round-num",
        "1",
        "--voter-files",
        str(voter),
        "--proposer-map-file",
        str(map_file),
        env={"IMPLEMENT_TMPDIR": ""},
    )
    assert result_attr.returncode == 0, result_attr.stderr
    assert result_neutral.returncode == 0, result_neutral.stderr
    row_attr = _tsv_rows(Path(rts.kv_get(result_attr.stdout, "FINDINGS_CLASSIFICATION_TSV_FILE") or ""))["FINDING_1"]
    row_neutral = _tsv_rows(Path(rts.kv_get(result_neutral.stdout, "FINDINGS_CLASSIFICATION_TSV_FILE") or ""))["FINDING_1"]
    assert row_attr["reviewer_slots"] == row_neutral["reviewer_slots"] == "Codex-Structure"


def test_neutralized_tally_restores_reviewer_in_accepted_artifact(tmp_path: Path) -> None:
    attributed = """### FINDING_1: First in-scope finding
- **Reviewer**: Codex-Structure
- **Concern**: Codex and Cursor disagree; Claude agrees.
- **Suggested revision**: Revision 1.
"""
    case = tmp_path / "restore-artifact"
    case.mkdir()
    ballot, map_file = _prepare_neutralized_ballot(case, attributed)
    voter = case / "v1.txt"
    _ = voter.write_text(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n",
        encoding="utf-8",
    )
    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(ballot),
        "--review-tmpdir",
        str(case),
        "--round-num",
        "1",
        "--voter-files",
        str(voter),
        "--proposer-map-file",
        str(map_file),
        env={"IMPLEMENT_TMPDIR": ""},
    )
    assert result.returncode == 0, result.stderr
    accepted = (case / "accepted-findings.md").read_text(encoding="utf-8")
    assert "- **Reviewer**: Codex-Structure" in accepted
    assert "Codex and Cursor disagree" in accepted
    assert "anonymous" not in accepted


def test_neutralized_tally_missing_sidecar_entry_fails_closed(tmp_path: Path) -> None:
    attributed = """### FINDING_1: First
- **Reviewer**: Codex-Structure
- **Concern**: one.

### FINDING_2: Second
- **Reviewer**: Cursor-Security
- **Concern**: two.
"""
    case = tmp_path / "missing-map-entry"
    case.mkdir()
    ballot, map_file = _prepare_neutralized_ballot(case, attributed)
    rows = map_file.read_text(encoding="utf-8").splitlines()
    _ = map_file.write_text("\n".join(rows[:2]) + "\n", encoding="utf-8")
    voter = case / "v1.txt"
    _ = voter.write_text("FINDING_1: YES\nFINDING_2: YES\n", encoding="utf-8")
    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(ballot),
        "--review-tmpdir",
        str(case),
        "--round-num",
        "1",
        "--voter-files",
        str(voter),
        "--proposer-map-file",
        str(map_file),
        env={"IMPLEMENT_TMPDIR": ""},
    )
    assert result.returncode != 0
    assert "missing proposer map entry" in result.stderr


def test_attributed_ballot_without_sidecar_keeps_legacy_reviewer_fallback(tmp_path: Path) -> None:
    case = tmp_path / "legacy-attributed"
    case.mkdir()
    _mk_ballot(case / "ballot.md")
    voter = case / "v1.txt"
    _ = voter.write_text(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n",
        encoding="utf-8",
    )
    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--review-tmpdir",
        str(case),
        "--round-num",
        "1",
        "--voter-files",
        str(voter),
        env={"IMPLEMENT_TMPDIR": ""},
    )
    assert result.returncode == 0, result.stderr
    row = _tsv_rows(Path(rts.kv_get(result.stdout, "FINDINGS_CLASSIFICATION_TSV_FILE") or ""))["FINDING_1"]
    assert row["reviewer_slots"] == "Codex-Structure"
