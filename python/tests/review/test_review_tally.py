from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

from larch.review import review_tally
import review_test_support as rts
from larch.review import voting

ROOT = rts.ROOT
CLI = rts.CLI

_CLASSIFICATION_HEADER = (
    "finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\t"
    "v1_quality\tv1_uncertain\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\t"
    "v2_uncertain\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain\tscope"
)

_CODE_REVIEW_CLASSIFICATION_HEADER = (
    "finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\t"
    "v1_quality\tv1_uncertain\tv1_tool\tv2_vote\tv2_correctness\tv2_severity\t"
    "v2_quality\tv2_uncertain\tv2_tool\tv3_vote\tv3_correctness\tv3_severity\t"
    "v3_quality\tv3_uncertain\tv3_tool\tscope"
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


def _tsv_row_list(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


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
    voting.write_proposer_map(ballot_file=ballot, map_file=map_file)
    _ = ballot.write_text(voting.neutralize_reviewer_attribution(text=attributed_text), encoding="utf-8")
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


def test_block_files_nests_under_review_tmpdir(tmp_path: Path) -> None:
    review_tmpdir = tmp_path / "review-tmp"
    review_tmpdir.mkdir()
    ballot = tmp_path / "ballot.md"
    _mk_ballot(ballot)

    blocks = review_tally._block_files(ballot_file=ballot, review_tmpdir=review_tmpdir)  # pyright: ignore[reportPrivateUsage]

    assert blocks
    for block in blocks:
        assert block.resolve().is_relative_to(review_tmpdir.resolve())


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
    assert rts.kv_get(stdout=result.stdout, key="ACCEPTED_COUNT") == "1"
    assert rts.kv_get(stdout=result.stdout, key="REJECTED_COUNT") == "1"
    assert rts.kv_get(stdout=result.stdout, key="OOS_ACCEPTED_COUNT") == "1"
    assert "FINDING_1: First in-scope finding" in (case / "accepted-findings.md").read_text(encoding="utf-8")
    assert "FINDING_2" in (case / "rejected-findings.md").read_text(encoding="utf-8")
    ledger_rows = _tsv_rows(case / "findings-ledger.tsv")
    assert set(ledger_rows) == {"FINDING_1", "FINDING_2", "FINDING_3"}
    assert ledger_rows["FINDING_1"]["outcome"] == "accepted"
    assert ledger_rows["FINDING_2"]["outcome"] == "neutral"
    assert ledger_rows["FINDING_3"]["outcome"] == "oos"
    assert "proposer" not in (case / "findings-ledger.tsv").read_text(encoding="utf-8").splitlines()[0]


def test_tally_rescues_high_severity_neutral_findings_to_oos(tmp_path: Path) -> None:
    case = tmp_path / "neutral-rescue"
    case.mkdir()
    _ = (case / "ballot.md").write_text(
        """### FINDING_1: High severity neutral
- **Reviewer**: Codex-Correctness
- **Concern**: High severity single-YES concern.
- **Suggested revision**: File this instead of dropping it.

### FINDING_2: Nit neutral
- **Reviewer**: Cursor-Testing
- **Concern**: Low severity single-YES concern.
- **Suggested revision**: Keep current neutral handling.
""",
        encoding="utf-8",
    )
    _ = (case / "v1.txt").write_text(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n"
        "FINDING_2: YES CORRECTNESS=true SEVERITY=nit QUALITY=adequate UNCERTAIN=false\n",
        encoding="utf-8",
    )
    for name in ("v2.txt", "v3.txt"):
        _ = (case / name).write_text(
            "FINDING_1: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n"
            "FINDING_2: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n",
            encoding="utf-8",
        )

    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--voter-files",
        str(case / "v1.txt"),
        str(case / "v2.txt"),
        str(case / "v3.txt"),
        "--review-tmpdir",
        str(case),
    )

    assert result.returncode == 0, result.stderr
    assert rts.kv_get(stdout=result.stdout, key="ACCEPTED_COUNT") == "0"
    assert rts.kv_get(stdout=result.stdout, key="OOS_REJECTED_COUNT") == "1"
    assert rts.kv_get(stdout=result.stdout, key="NEUTRAL_COUNT") == "1"
    assert rts.kv_get(stdout=result.stdout, key="REJECTED_COUNT") == "1"
    oos = (case / "oos.md").read_text(encoding="utf-8")
    rejected = (case / "rejected-findings.md").read_text(encoding="utf-8")
    assert "FINDING_1" in oos
    assert "neutral-rescued" in oos
    assert "FINDING_1" not in rejected
    assert "FINDING_2" in rejected
    tally_env = (case / "review-tally.env").read_text(encoding="utf-8")
    assert "FINDING_1_OUTCOME=oos\n" in tally_env
    assert "FINDING_1_REJECTED_SUBTYPE=" not in tally_env
    rows = _tsv_rows(Path(rts.kv_get(stdout=result.stdout, key="FINDINGS_CLASSIFICATION_TSV_FILE") or ""))
    assert rows["FINDING_1"]["scope"] == "oos"
    assert rows["FINDING_1"]["voting_result"] == "neutral"
    assert rows["FINDING_2"]["scope"] == "in_scope"
    assert rows["FINDING_2"]["voting_result"] == "neutral"
    ledger_rows = _tsv_rows(case / "findings-ledger.tsv")
    assert ledger_rows["FINDING_1"]["outcome"] == "oos"

    emit = run_review(
        "emit-tally",
        "--tally-file",
        str(case / "review-tally.env"),
        "--accepted-findings-file",
        str(case / "accepted-findings.md"),
        "--oos-file",
        str(case / "oos.md"),
        "--review-tmpdir",
        str(case),
        "--round",
        "1",
        "--mode",
        "diff",
    )

    assert emit.returncode == 0, emit.stderr
    rebuilt_rejected = (case / "rejected-findings.md").read_text(encoding="utf-8")
    assert "FINDING_1" not in rebuilt_rejected
    assert "FINDING_2: Nit neutral" in rebuilt_rejected
    assert "Low severity single-YES concern" in rebuilt_rejected
    assert "Vote tally: YES=1 NO=2 JUDGE_ERROR=0" in rebuilt_rejected

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
        str(case),
    )
    assert write_round.returncode == 0, write_round.stderr
    committed_rejected = (log_root / "implement" / "run-a" / "round-1" / "rejected-findings.md").read_text(
        encoding="utf-8"
    )
    assert "FINDING_2: Nit neutral" in committed_rejected
    assert "Low severity single-YES concern" in committed_rejected


def test_tally_flags_under_quorum_findings(tmp_path: Path) -> None:
    # Issue #4880: two of three voters JUDGE_ERROR (by omitting their votes) on a trailing finding
    # while staying under the per-voter parse-rate removal threshold, so the panel silently collapses
    # to a single voter for that finding. The tally must flag it and surface a run-summary warning.
    case = tmp_path / "under-quorum"
    case.mkdir()
    ballot = "".join(
        f"### FINDING_{n}: In-scope finding {n}\n"
        "- **Reviewer**: Cursor-Correctness\n"
        f"- **Concern**: bug {n}.\n"
        f"- **Suggested revision**: fix {n}.\n\n"
        for n in range(1, 6)
    )
    _ = (case / "ballot.md").write_text(ballot, encoding="utf-8")
    full = "".join(
        f"FINDING_{n}: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n"
        for n in range(1, 6)
    )
    # codex and claude omit FINDING_5 only (1/5 = 20% JUDGE_ERROR, below the 80% removal threshold),
    # so both remain in the effective quorum even though FINDING_5 loses two of three votes.
    partial = "".join(
        f"FINDING_{n}: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n"
        for n in range(1, 5)
    )
    _ = (case / "cursor-vote-output.txt").write_text(full, encoding="utf-8")
    _ = (case / "codex-vote-output.txt").write_text(partial, encoding="utf-8")
    _ = (case / "claude-vote-output.txt").write_text(partial, encoding="utf-8")
    exec_log = tmp_path / "execution-issues.md"

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
        env={"LARCH_EXECUTION_ISSUES_LOG": str(exec_log)},
    )

    assert result.returncode == 0, result.stderr
    # Neither partial voter is removed from quorum (20% < 80%), so the panel size stays 3.
    assert rts.kv_get(stdout=result.stdout, key="VOTER_COUNT") == "3"
    # Only FINDING_5 dropped below the 2-of-3 majority quorum.
    assert rts.kv_get(stdout=result.stdout, key="UNDER_QUORUM_COUNT") == "1"
    # Issue #5334: UNDER_QUORUM_ITEMS carries the item list so the caller can surface the warning
    # after the retry decision is settled (tally-code-votes no longer writes to execution-issues.md).
    assert rts.kv_get(stdout=result.stdout, key="UNDER_QUORUM_ITEMS") == "FINDING_5"
    tally = (case / "voting-tally.md").read_text(encoding="utf-8")
    assert "| FINDING_5 | 0 | 1 | 2 |" in tally
    assert "decided below the 2-of-3 panel quorum" in tally
    # Issue #5334: tally-code-votes must NOT write the under-quorum execution-issues warning;
    # that is deferred to _run_round in review_and_fix.py after the retry decision.
    assert not exec_log.is_file()


def test_tally_weighted_scoreboard_major_oos_and_coproposers(tmp_path: Path) -> None:
    case = tmp_path / "weighted-scoreboard"
    case.mkdir()
    _ = (case / "ballot.md").write_text(
        """### FINDING_1: Major in-scope
- **Reviewer**: Codex-Correctness
- **Concern**: Major bug.
- **Suggested revision**: Fix.

### FINDING_2: Minor in-scope
- **Reviewer**: Cursor-Testing
- **Concern**: Minor issue.
- **Suggested revision**: Fix.

### FINDING_3: Co-proposed blocker
- **Reviewer(s)**: Codex-Arch, Cursor-Testing
- **Concern**: Shared blocker.
- **Suggested revision**: Fix.

### FINDING_4: Neutral in-scope
- **Reviewer**: Codex-Neutral
- **Concern**: Borderline issue.
- **Suggested revision**: Fix.

### OOS_1: [OUT_OF_SCOPE] High severity OOS
- **Reviewer**: Codex-Edge
- **Concern**: Future work.
- **Suggested revision**: File it.

### OOS_2: [OUT_OF_SCOPE] Neutral OOS
- **Reviewer**: Codex-OOS-Neutral
- **Concern**: Borderline future work.
- **Suggested revision**: File it.
""",
        encoding="utf-8",
    )
    yes_votes = (
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n"
        "FINDING_2: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n"
        "FINDING_3: YES CORRECTNESS=true SEVERITY=blocker QUALITY=good UNCERTAIN=false\n"
        "FINDING_4: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n"
        "OOS_1: YES CORRECTNESS=true SEVERITY=blocker QUALITY=good UNCERTAIN=false\n"
        "OOS_2: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n"
    )
    no_votes = (
        "FINDING_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n"
        "FINDING_2: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n"
        "FINDING_3: YES CORRECTNESS=true SEVERITY=blocker QUALITY=good UNCERTAIN=false\n"
        "FINDING_4: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n"
        "OOS_1: YES CORRECTNESS=true SEVERITY=blocker QUALITY=good UNCERTAIN=false\n"
        "OOS_2: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n"
    )
    _ = (case / "cursor-vote-output.txt").write_text(yes_votes, encoding="utf-8")
    for name in ("codex-vote-output.txt", "claude-vote-output.txt"):
        _ = (case / name).write_text(no_votes, encoding="utf-8")

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
    tally = (case / "voting-tally.md").read_text(encoding="utf-8")
    assert "| Codex-Correctness | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |" in tally
    assert "| Cursor-Testing | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |" in tally
    assert "| Codex-Arch | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |" in tally
    assert "| Codex-Edge | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 |" in tally
    assert "| Codex-Neutral | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | -0.25 |" in tally
    assert "| Codex-OOS-Neutral | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 |" in tally
    assert "Unique finder bonus active" not in tally

    class_file = Path(rts.kv_get(stdout=result.stdout, key="FINDINGS_CLASSIFICATION_TSV_FILE") or "")
    tsv_rows = _tsv_rows(class_file)
    assert tsv_rows["OOS_1"]["scope"] == "oos"
    assert tsv_rows["OOS_2"]["scope"] == "oos"
    assert tsv_rows["FINDING_1"]["scope"] == "in_scope"


def test_tally_majority_high_yes_severities_score_plus_two(tmp_path: Path) -> None:
    case = tmp_path / "majority-high-severities"
    case.mkdir()
    _ = (case / "ballot.md").write_text(
        """### FINDING_1: Majority-high severities
- **Reviewer**: Codex-Majority
- **Concern**: Important bug.
- **Suggested revision**: Fix.

### FINDING_2: Majority-high with dissenting NO
- **Reviewer**: Cursor-Dissent
- **Concern**: Important bug with one NO voter.
- **Suggested revision**: Fix.
""",
        encoding="utf-8",
    )
    v1 = (
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n"
        "FINDING_2: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n"
    )
    v2 = (
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n"
        "FINDING_2: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n"
    )
    v3 = (
        "FINDING_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n"
        "FINDING_2: NO CORRECTNESS=false-positive SEVERITY=minor QUALITY=no-fix UNCERTAIN=false\n"
    )
    _ = (case / "cursor-vote-output.txt").write_text(v1, encoding="utf-8")
    _ = (case / "codex-vote-output.txt").write_text(v2, encoding="utf-8")
    _ = (case / "claude-vote-output.txt").write_text(v3, encoding="utf-8")

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
    tally = (case / "voting-tally.md").read_text(encoding="utf-8")
    assert "| Codex-Majority | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |" in tally
    assert "| Cursor-Dissent | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |" in tally


def test_tally_unique_finder_bonus_rewards_only_sole_in_scope_findings(tmp_path: Path) -> None:
    case = tmp_path / "unique-finder-bonus"
    case.mkdir()
    _ = (case / "ballot.md").write_text(
        """### FINDING_1: Sole minor in-scope
- **Reviewer**: Cursor-Solo
- **Concern**: Real issue.
- **Suggested revision**: Fix.

### FINDING_2: Shared minor in-scope
- **Reviewer(s)**: Codex-Arch, Cursor-Testing
- **Concern**: Shared issue.
- **Suggested revision**: Fix.

### OOS_1: Future work
- **Reviewer**: Codex-OOS
- **Concern**: Future issue.
- **Suggested revision**: File it.
""",
        encoding="utf-8",
    )
    votes = (
        "FINDING_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false\n"
        "FINDING_2: YES CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false\n"
        "OOS_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n"
    )
    for name in ("cursor-vote-output.txt", "codex-vote-output.txt", "claude-vote-output.txt"):
        _ = (case / name).write_text(votes, encoding="utf-8")

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
        env={"LARCH_UNIQUE_FINDER_BONUS": "0.25"},
    )

    assert result.returncode == 0, result.stderr
    tally = (case / "voting-tally.md").read_text(encoding="utf-8")
    assert "| Cursor-Solo | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1.25 |" in tally
    assert "| Codex-Arch | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |" in tally
    assert "| Cursor-Testing | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |" in tally
    assert "| Codex-OOS | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 |" in tally
    assert "**Unique finder bonus active:** 1 accepted in-scope sole-finder finding(s) received +0.25 each." in tally


def test_tally_scope_drift_oos_scoring_stays_flat(tmp_path: Path) -> None:
    case = tmp_path / "scope-drift-score"
    case.mkdir()
    _ = (case / "ballot.md").write_text(
        """### FINDING_1: **Important** — `code-quality` — `docs/linting.md:22`
- **Reviewer**: Cursor-Correctness
- **Concern**: Out-of-diff docs drift.
- **Suggested revision**: Update docs.
""",
        encoding="utf-8",
    )
    _ = (case / "scope-files.txt").write_text("python/cli.py\n", encoding="utf-8")
    votes = "FINDING_1: YES CORRECTNESS=true SEVERITY=blocker QUALITY=good UNCERTAIN=false\n"
    for name in ("cursor-vote-output.txt", "codex-vote-output.txt", "claude-vote-output.txt"):
        _ = (case / name).write_text(votes, encoding="utf-8")

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
        env={"LARCH_UNIQUE_FINDER_BONUS": "0.25"},
    )

    assert result.returncode == 0, result.stderr
    class_file = Path(rts.kv_get(stdout=result.stdout, key="FINDINGS_CLASSIFICATION_TSV_FILE") or "")
    tsv_rows = _tsv_rows(class_file)
    assert tsv_rows["FINDING_1"]["scope"] == "oos"
    tally = (case / "voting-tally.md").read_text(encoding="utf-8")
    assert "| Cursor-Correctness | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 |" in tally
    assert "Unique finder bonus active" not in tally


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
    assert rts.kv_get(stdout=result.stdout, key="ELIGIBLE_VOTER_COUNT") == "3"
    assert rts.kv_get(stdout=result.stdout, key="VOTER_COUNT") == "2"
    assert rts.kv_get(stdout=result.stdout, key="PARSE_FAILED_COUNT") == "1"
    assert rts.kv_get(stdout=result.stdout, key="TALLY_STATUS") == "ok"
    tally = (case / "voting-tally.md").read_text(encoding="utf-8")
    assert "narrative-only output" in tally
    assert "parse-rate" in tally
    assert "## Voter Agreement Scoreboard" in tally
    assert "## Voter Severity Scoreboard" in tally
    assert tally.index("## Voter Agreement Scoreboard") < tally.index("## Voter Severity Scoreboard")
    assert "| code-review | v1 |" in tally
    assert "| code-review | v2 |" in tally
    assert "| code-review | v3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | false |" in tally
    class_file = Path(rts.kv_get(stdout=result.stdout, key="FINDINGS_CLASSIFICATION_TSV_FILE") or "")
    assert class_file.is_file()
    class_text = class_file.read_text(encoding="utf-8")
    assert class_text.splitlines()[0] == _CLASSIFICATION_HEADER
    tsv_records = voting.compute_voter_agreement(
        voting.voter_agreement_rows_from_tsv(class_text, panel_kind="code-review").rows
    )
    for record in tsv_records:
        rate = "n/a" if record["agreement_rate"] is None else f"{float(record['agreement_rate']):.3f}"  # pyright: ignore[reportArgumentType]
        line = (
            f"| code-review | {record['voter']} | {record['eligible']} | {record['agree']} | "
            f"{record['disagree']} | {record['missing']} | {rate} | "
            f"{str(bool(record['outlier'])).lower()} |"
        )
        assert line in tally


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
    assert rts.kv_get(stdout=result.stdout, key="OOS_ACCEPTED_COUNT") == "0"
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
    assert rts.kv_get(stdout=result.stdout, key="OUT_OF_SCOPE_DRIFT_COUNT") == "1"
    assert rts.kv_get(stdout=result.stdout, key="ACCEPTED_COUNT") == "1"
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
    assert rts.kv_get(stdout=result.stdout, key="OUT_OF_SCOPE_DRIFT_COUNT") == "0"
    assert rts.kv_get(stdout=result.stdout, key="ACCEPTED_COUNT") == "1"
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
    assert rts.kv_get(stdout=result.stdout, key="TALLY_STATUS") == "main-agent-vote-required"
    assert rts.kv_get(stdout=result.stdout, key="VOTER_COUNT") == "0"
    tally = (case / "voting-tally.md").read_text(encoding="utf-8")
    assert "fake agreement" not in tally
    assert "## Voter Agreement Scoreboard" in tally
    assert "## Voter Severity Scoreboard" in tally
    assert tally.index("## Voter Agreement Scoreboard") < tally.index("## Voter Severity Scoreboard")
    assert "| undefined | n/a | 0 | 0 | 0 | 0 | n/a | false |" in tally


def test_tally_all_narrative_voters_emits_parse_failed_count_on_zero_effective(tmp_path: Path) -> None:
    case = tmp_path / "all-narrative"
    case.mkdir()
    _mk_ballot(case / "ballot.md")
    _ = (case / "cursor-vote-output.txt").write_text("narrative only\n", encoding="utf-8")
    _ = (case / "codex-vote-output.txt").write_text("narrative only\n", encoding="utf-8")
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
    assert rts.kv_get(stdout=result.stdout, key="TALLY_STATUS") == "main-agent-vote-required"
    assert rts.kv_get(stdout=result.stdout, key="VOTER_COUNT") == "0"
    assert rts.kv_get(stdout=result.stdout, key="PARSE_FAILED_COUNT") == "3"
    tally = (case / "voting-tally.md").read_text(encoding="utf-8")
    assert "narrative-only output" in tally


def test_tally_empty_ballot_skips_vote_without_degraded_warning(tmp_path: Path) -> None:
    case = tmp_path / "empty-ballot"
    case.mkdir()
    _ = (case / "ballot.md").write_text("", encoding="utf-8")
    voter = case / "zero-findings-voter.txt"
    _ = voter.write_text("", encoding="utf-8")

    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--voter-files",
        str(voter),
        "--review-tmpdir",
        str(case),
    )

    assert result.returncode == 0, result.stderr
    assert rts.kv_get(stdout=result.stdout, key="TALLY_STATUS") == "skipped-empty-findings"
    assert rts.kv_get(stdout=result.stdout, key="VOTER_COUNT") == "0"
    assert rts.kv_get(stdout=result.stdout, key="PARSE_FAILED_COUNT") == "0"
    class_file = Path(rts.kv_get(stdout=result.stdout, key="FINDINGS_CLASSIFICATION_TSV_FILE") or "")
    assert class_file.read_text(encoding="utf-8") == _CLASSIFICATION_HEADER + "\n"
    tally = (case / "voting-tally.md").read_text(encoding="utf-8")
    assert "Round skipped: no findings to adjudicate." in tally
    assert "⚠ Degraded code-review panel" not in tally
    assert "narrative-only output" not in tally


def test_tally_security_classifier_failure_fails_closed(tmp_path: Path) -> None:
    case = tmp_path / "security-classifier-fail"
    case.mkdir()
    bin_dir = case / "bin"
    bin_dir.mkdir()
    rts.write_executable(
        path=bin_dir / "python3",
        body="""#!/usr/bin/env bash
exit 1
"""
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
    class_file = Path(rts.kv_get(stdout=result.stdout, key="FINDINGS_CLASSIFICATION_TSV_FILE") or "")
    assert class_file == round_dir / "findings-classification.tsv"
    header = class_file.read_text(encoding="utf-8").splitlines()[0]
    assert header == _CLASSIFICATION_HEADER
    rows = _tsv_rows(class_file)
    finding = rows["FINDING_1"]
    assert finding["voting_result"] == "accepted"
    assert finding["reviewer_slots"] == "cursor-a-output.txt|codex-b-output.txt"
    assert finding["v1_vote"] == "YES"
    assert finding["v2_vote"] == "YES"
    assert finding["scope"] == "in_scope"
    assert rows["OOS_1"]["voting_result"] == "neutral"
    assert rows["OOS_1"]["scope"] == "oos"
    ledger = impl_parent / "findings-ledger.tsv"
    ledger_rows = _tsv_rows(ledger)
    assert ledger_rows["FINDING_1"]["round"] == "1"
    assert ledger_rows["FINDING_1"]["outcome"] == "accepted"
    assert ledger_rows["OOS_1"]["outcome"] == "oos"

    round2 = impl_parent / "round-2"
    round2.mkdir()
    _write_classification_ballot(round2 / "ballot.md")
    for name in ("v1.txt", "v2.txt"):
        _ = (round2 / name).write_text((round_dir / name).read_text(encoding="utf-8"), encoding="utf-8")
    result2 = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(round2 / "ballot.md"),
        "--review-tmpdir",
        str(round2),
        "--session-env-path",
        str(impl_parent / "session-env.sh"),
        "--round-num",
        "2",
        "--voter-files",
        str(round2 / "v1.txt"),
        str(round2 / "v2.txt"),
        env={"IMPLEMENT_TMPDIR": str(impl_parent)},
    )
    assert result2.returncode == 0, result2.stderr
    assert [row["round"] for row in _tsv_row_list(ledger)] == ["1", "1", "2", "2"]
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
    class_file = Path(rts.kv_get(stdout=result.stdout, key="FINDINGS_CLASSIFICATION_TSV_FILE") or "")
    assert class_file == case / "findings-classification-round-1.tsv"
    row = _tsv_rows(class_file)["FINDING_1"]
    assert row["voting_result"] == "accepted"
    assert row["v2_vote"] == "YES"
    assert row["v2_correctness"] == ""
    assert row["v2_uncertain"] == "true"
    assert row["scope"] == "in_scope"


def test_tally_code_review_voter_agreement_scoreboard_three_slot(tmp_path: Path) -> None:
    case = tmp_path / "voter-scoreboard"
    case.mkdir()
    _mk_ballot(case / "ballot.md")
    _ = (case / "v1.txt").write_text(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n"
        "FINDING_2: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n"
        "FINDING_3: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n",
        encoding="utf-8",
    )
    _ = (case / "v2.txt").write_text(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n"
        "FINDING_2: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n"
        "FINDING_3: YES CORRECTNESS=true SEVERITY=major QUALITY=adequate UNCERTAIN=false\n",
        encoding="utf-8",
    )
    _ = (case / "v3.txt").write_text(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n"
        "FINDING_2: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n"
        "FINDING_3: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n",
        encoding="utf-8",
    )
    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--review-tmpdir",
        str(case),
        "--cursor-available",
        "true",
        "--voter-files",
        str(case / "v1.txt"),
        str(case / "v2.txt"),
        str(case / "v3.txt"),
        "--voter-tools",
        "cursor-validity",
        "cursor-plan-fidelity",
        "cursor-pragmatism",
        env={"CLAUDE_PLUGIN_ROOT": str(ROOT)},
    )
    assert result.returncode == 0, result.stderr
    tally = (case / "voting-tally.md").read_text(encoding="utf-8")
    assert "| Codex-Structure |" in tally
    class_file = Path(rts.kv_get(stdout=result.stdout, key="FINDINGS_CLASSIFICATION_TSV_FILE") or "")
    tsv_records = voting.compute_voter_agreement(
        voting.voter_agreement_rows_from_tsv(class_file.read_text(encoding="utf-8"), panel_kind="code-review").rows
    )
    assert "## Voter Agreement Scoreboard" in tally
    assert "## Voter Severity Scoreboard" in tally
    assert tally.index("## Voter Agreement Scoreboard") < tally.index("## Voter Severity Scoreboard")
    assert "| code-review | cursor-plan-fidelity | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 1.000 | 0.000 | true |" in tally
    for record in tsv_records:
        rate = "n/a" if record["agreement_rate"] is None else f"{float(record['agreement_rate']):.3f}"  # pyright: ignore[reportArgumentType]
        line = (
            f"| code-review | {record['voter']} | {record['eligible']} | {record['agree']} | "
            f"{record['disagree']} | {record['missing']} | {rate} | "
            f"{str(bool(record['outlier'])).lower()} |"
        )
        assert line in tally


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
    class_file = Path(rts.kv_get(stdout=result.stdout, key="FINDINGS_CLASSIFICATION_TSV_FILE") or "")
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
    class_file = Path(rts.kv_get(stdout=result.stdout, key="FINDINGS_CLASSIFICATION_TSV_FILE") or "")
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
    assert rts.kv_get(stdout=result.stdout, key="TALLY_STATUS") == "main-agent-vote-required"
    class_file = Path(rts.kv_get(stdout=result.stdout, key="FINDINGS_CLASSIFICATION_TSV_FILE") or "")
    header = class_file.read_text(encoding="utf-8").splitlines()[0]
    assert header == _CLASSIFICATION_HEADER
    rows_by_id = _tsv_rows(class_file)
    assert len(rows_by_id) == 2
    expected_cols = set(_CLASSIFICATION_HEADER.split("\t"))
    for row in rows_by_id.values():
        assert set(row.keys()) == expected_cols
        assert row["voting_result"] == "rejected"
        for key, value in row.items():
            if len(key) > 2 and key[0] == "v" and key[1].isdigit() and key[2] == "_":
                assert value == ""
    assert rows_by_id["FINDING_1"]["scope"] == "in_scope"
    assert rows_by_id["OOS_1"]["scope"] == "oos"
    assert not (case / "findings-ledger.tsv").exists()


def test_tally_code_review_mav_retally_ledger_lifecycle(tmp_path: Path) -> None:
    case = tmp_path / "mav-ledger"
    case.mkdir()
    _write_classification_ballot(case / "ballot.md")
    v1 = case / "v1.txt"
    v2 = case / "v2.txt"
    for voter in (v1, v2):
        _ = voter.write_text(
            "FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n"
            "OOS_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false\n",
            encoding="utf-8",
        )

    mav = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--review-tmpdir",
        str(case),
        env={"IMPLEMENT_TMPDIR": ""},
    )
    assert mav.returncode == 0, mav.stderr
    assert rts.kv_get(stdout=mav.stdout, key="TALLY_STATUS") == "main-agent-vote-required"
    assert not (case / "findings-ledger.tsv").exists()

    final = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--review-tmpdir",
        str(case),
        "--voter-files",
        str(v1),
        str(v2),
        env={"IMPLEMENT_TMPDIR": ""},
    )
    assert final.returncode == 0, final.stderr
    ledger = case / "findings-ledger.tsv"
    assert ledger.is_file()
    rows = _tsv_row_list(ledger)
    assert len(rows) == 2
    assert rows[0]["outcome"] == "accepted"

    _ = v1.write_text(
        "FINDING_1: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n"
        "OOS_1: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n",
        encoding="utf-8",
    )
    _ = v2.write_text(
        "FINDING_1: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n"
        "OOS_1: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n",
        encoding="utf-8",
    )
    retally = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--review-tmpdir",
        str(case),
        "--round-num",
        "1",
        "--voter-files",
        str(v1),
        str(v2),
        env={"IMPLEMENT_TMPDIR": ""},
    )
    assert retally.returncode == 0, retally.stderr
    rows = _tsv_row_list(ledger)
    assert len(rows) == 2
    assert all(row["round"] == "1" for row in rows)
    assert rows[0]["outcome"] == "rejected"


def test_tally_accepted_latent_finding_ledger_outcome_is_accepted(tmp_path: Path) -> None:
    case = tmp_path / "latent-accepted"
    case.mkdir()
    _ = (case / "ballot.md").write_text(
        """### FINDING_1: Latent accepted item
- **Reviewer**: Codex-Correctness
- **Severity**: latent
- **Concern**: Real but latent concern.
- **Suggested revision**: Fix later.
""",
        encoding="utf-8",
    )
    _ = (case / "v1.txt").write_text(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=latent QUALITY=good UNCERTAIN=false\n",
        encoding="utf-8",
    )
    _ = (case / "v2.txt").write_text(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=latent QUALITY=adequate UNCERTAIN=false\n",
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
        str(case / "v2.txt"),
        env={"IMPLEMENT_TMPDIR": ""},
    )
    assert result.returncode == 0, result.stderr
    ledger_rows = _tsv_rows(case / "findings-ledger.tsv")
    assert ledger_rows["FINDING_1"]["outcome"] == "accepted"


def test_ledger_reason_ignores_unlabeled_ballot_bullets() -> None:
    block = """### FINDING_1: Example
- **Reviewer**: Codex-Structure
- **Concern**: Real issue.
- **Suggested fix:** Do the thing.
### In-Scope Findings
"""
    assert review_tally._ledger_reason(block) == "Real issue."  # pyright: ignore[reportPrivateUsage]
    assert "**Suggested fix:**" not in review_tally._ledger_reason(block)  # pyright: ignore[reportPrivateUsage]
    assert "### In-Scope Findings" not in review_tally._ledger_reason(block)  # pyright: ignore[reportPrivateUsage]
    bare = """### FINDING_2: Bare
- **Reviewer**: Codex-Structure
- bullet without label
"""
    assert review_tally._ledger_reason(bare) == ""  # pyright: ignore[reportPrivateUsage]


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
    class_file = Path(rts.kv_get(stdout=result.stdout, key="FINDINGS_CLASSIFICATION_TSV_FILE") or "")
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
        class_file = Path(rts.kv_get(stdout=result.stdout, key="FINDINGS_CLASSIFICATION_TSV_FILE") or "")
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
        parser_vote = rts.kv_get(stdout=parsed.stdout, key="PARSED_VOTE")
        lib = _run_cli("voting", "vote-for-id", finding_id, str(votes))
        assert lib.returncode == 0, lib.stderr
        assert parser_vote == lib.stdout.strip()
    missing = _run_cli("voting", "parse-judge-vote", str(votes), "FINDING_2")
    assert rts.kv_get(stdout=missing.stdout, key="PARSED_VOTE") == ""


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
    row = _tsv_rows(Path(rts.kv_get(stdout=result.stdout, key="FINDINGS_CLASSIFICATION_TSV_FILE") or ""))["FINDING_1"]
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
    row = _tsv_rows(Path(rts.kv_get(stdout=result.stdout, key="FINDINGS_CLASSIFICATION_TSV_FILE") or ""))["FINDING_1"]
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
    for row in _tsv_rows(Path(rts.kv_get(stdout=result.stdout, key="FINDINGS_CLASSIFICATION_TSV_FILE") or "")).values():
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
    class_file = Path(rts.kv_get(stdout=result.stdout, key="FINDINGS_CLASSIFICATION_TSV_FILE") or "")
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
    assert rts.kv_get(stdout=result.stdout, key="ELIGIBLE_VOTER_COUNT") == "2"
    class_file = Path(rts.kv_get(stdout=result.stdout, key="FINDINGS_CLASSIFICATION_TSV_FILE") or "")
    lines = class_file.read_text(encoding="utf-8").splitlines()
    assert lines[0] == _CODE_REVIEW_CLASSIFICATION_HEADER
    assert all(len(line.split("\t")) == 22 for line in lines)
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


def test_write_tally_allows_voter_agreement_scoreboard_header(tmp_path: Path) -> None:
    body = tmp_path / "body.md"
    _ = body.write_text(
        "# Code Review Voting Tally\n\n"
        "## Per-finding vote breakdown\n\n"
        "## Reviewer Competition Scoreboard\n\n"
        "## Voter Agreement Scoreboard\n\n"
        "## Voter Severity Scoreboard\n\n",
        encoding="utf-8",
    )
    result = _run_cli(
        "voting",
        "write-tally",
        "--log-root",
        str(tmp_path / "logs"),
        "--skill",
        "review",
        "--run-id",
        "run-a",
        "--phase",
        "code-review",
        "--mode",
        "hard",
        "--rounds",
        "1",
        "--accepted",
        "0",
        "--rejected",
        "0",
        "--body-file",
        str(body),
    )
    assert result.returncode == 0, result.stderr
    assert "unrecognized section header" not in result.stderr


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
    assert rts.kv_get(stdout=result.stdout, key="VOTER_COUNT") == "1"
    row = _tsv_rows(Path(rts.kv_get(stdout=result.stdout, key="FINDINGS_CLASSIFICATION_TSV_FILE") or ""))["FINDING_1"]
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


def test_emit_tally_round_summary_uses_voting_tally_counts(tmp_path: Path) -> None:
    case = tmp_path / "summary-counts"
    case.mkdir()
    tally = case / "review-tally.env"
    _ = tally.write_text("ACCEPTED_COUNT=0\nREJECTED_COUNT=1\nNEUTRAL_COUNT=0\n", encoding="utf-8")
    _ = (case / "voting-tally.md").write_text(
        "## Findings\n\n"
        "| Item | Result |\n"
        "|---|---|\n"
        "| FINDING_1 | rejected |\n"
        "| FINDING_2 | rejected |\n",
        encoding="utf-8",
    )
    accepted = case / "accepted-findings.md"
    _ = accepted.write_text("", encoding="utf-8")
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
    assert "0 accepted, 2 rejected" in (case / "review-round-summary.md").read_text(encoding="utf-8")


def test_emit_tally_round_summary_prefers_round_meta_tally_counts(tmp_path: Path) -> None:
    case = tmp_path / "summary-counts-round-meta"
    case.mkdir()
    tally = case / "review-tally.env"
    _ = tally.write_text("ACCEPTED_COUNT=0\nREJECTED_COUNT=7\nNEUTRAL_COUNT=0\n", encoding="utf-8")
    _ = (case / "voting-tally.md").write_text(
        "## Findings\n\n"
        "| Item | Result |\n"
        "|---|---|\n"
        "| FINDING_1 | rejected |\n",
        encoding="utf-8",
    )
    _ = (case / "round-meta.json").write_text(
        json.dumps({"tally": {"ACCEPTED_COUNT": "0", "REJECTED_COUNT": "8", "NEUTRAL_COUNT": "0"}}),
        encoding="utf-8",
    )
    accepted = case / "accepted-findings.md"
    _ = accepted.write_text("", encoding="utf-8")
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
    assert "0 accepted, 8 rejected" in (case / "review-round-summary.md").read_text(encoding="utf-8")


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
    assert rts.kv_get(stdout=result.stdout, key="YIELD_TSV_FILE")
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
    row_attr = _tsv_rows(Path(rts.kv_get(stdout=result_attr.stdout, key="FINDINGS_CLASSIFICATION_TSV_FILE") or ""))["FINDING_1"]
    row_neutral = _tsv_rows(Path(rts.kv_get(stdout=result_neutral.stdout, key="FINDINGS_CLASSIFICATION_TSV_FILE") or ""))["FINDING_1"]
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
    header_idx = next(i for i, row in enumerate(rows) if row.startswith("item_id\t"))
    _ = map_file.write_text("\n".join(rows[: header_idx + 1]) + "\n", encoding="utf-8")
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
    assert "missing proposer map entry" in result.stderr or "proposer map item mismatch" in result.stderr


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
    row = _tsv_rows(Path(rts.kv_get(stdout=result.stdout, key="FINDINGS_CLASSIFICATION_TSV_FILE") or ""))["FINDING_1"]
    assert row["reviewer_slots"] == "Codex-Structure"


def test_neutralized_tally_auto_binds_default_sidecar(tmp_path: Path) -> None:
    attributed = """### FINDING_1: First in-scope finding
- **Reviewer**: Codex-Structure
- **Concern**: Codex and Cursor disagree; Claude agrees.
- **Suggested revision**: Revision 1.
"""
    case = tmp_path / "auto-bind-sidecar"
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
        env={"IMPLEMENT_TMPDIR": ""},
    )
    assert result.returncode == 0, result.stderr
    row = _tsv_rows(Path(rts.kv_get(stdout=result.stdout, key="FINDINGS_CLASSIFICATION_TSV_FILE") or ""))["FINDING_1"]
    assert row["reviewer_slots"] == "Codex-Structure"
    assert map_file.is_file()


def test_neutralized_tally_without_sidecar_fails_closed(tmp_path: Path) -> None:
    attributed = """### FINDING_1: First
- **Reviewer**: Codex-Structure
- **Concern**: one.
"""
    case = tmp_path / "neutral-no-sidecar"
    case.mkdir()
    ballot = case / "ballot.md"
    _ = ballot.write_text(voting.neutralize_reviewer_attribution(text=attributed), encoding="utf-8")
    voter = case / "v1.txt"
    _ = voter.write_text("FINDING_1: YES\n", encoding="utf-8")
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
        env={"IMPLEMENT_TMPDIR": ""},
    )
    assert result.returncode != 0
    assert "missing proposer map entry" in result.stderr


def test_attributed_ballot_ignores_stale_sidecar(tmp_path: Path) -> None:
    stale_attributed = """### FINDING_1: Old round
- **Reviewer**: Codex-Structure
- **Concern**: stale.
"""
    current_attributed = """### FINDING_1: Current round
- **Reviewer**: Cursor-Testing
- **Concern**: current.
"""
    case = tmp_path / "stale-sidecar"
    case.mkdir()
    stale_ballot = case / "stale.md"
    _ = stale_ballot.write_text(stale_attributed, encoding="utf-8")
    voting.write_proposer_map(ballot_file=stale_ballot, map_file=case / "proposer-map.tsv")
    ballot = case / "ballot.md"
    _ = ballot.write_text(current_attributed, encoding="utf-8")
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
        env={"IMPLEMENT_TMPDIR": ""},
    )
    assert result.returncode == 0, result.stderr
    row = _tsv_rows(Path(rts.kv_get(stdout=result.stdout, key="FINDINGS_CLASSIFICATION_TSV_FILE") or ""))["FINDING_1"]
    assert row["reviewer_slots"] == "Cursor-Testing"


def test_neutralized_ballot_rejects_stale_sidecar(tmp_path: Path) -> None:
    stale_attributed = """### FINDING_1: Old round
- **Reviewer**: Codex-Structure
- **Concern**: stale.
"""
    current_attributed = """### FINDING_1: Current round
- **Reviewer**: Cursor-Testing
- **Concern**: current.
"""
    case = tmp_path / "stale-neutral-sidecar"
    case.mkdir()
    stale_ballot = case / "stale.md"
    _ = stale_ballot.write_text(stale_attributed, encoding="utf-8")
    voting.write_proposer_map(ballot_file=stale_ballot, map_file=case / "proposer-map.tsv")
    ballot = case / "ballot.md"
    _ = ballot.write_text(voting.neutralize_reviewer_attribution(text=current_attributed), encoding="utf-8")
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
        env={"IMPLEMENT_TMPDIR": ""},
    )
    assert result.returncode != 0
    assert "stale for current ballot" in result.stderr


def test_tally_seed_oos_seq_counts_mixed_oos_and_finding_headings(tmp_path: Path) -> None:
    session_env = tmp_path / "session-env.sh"
    _ = session_env.write_text("RUN_ID=x\n", encoding="utf-8")
    _ = (tmp_path / "accumulated-oos.md").write_text(
        "### OOS_1: old\nbody\n"
        "### FINDING_2: legacy finding-shaped OOS\nbody\n"
        "### OOS_3: old\nbody\n",
        encoding="utf-8",
    )

    assert review_tally._seed_oos_seq(str(session_env)) == 3  # pyright: ignore[reportPrivateUsage]


def test_log_phase_forwards_dash_leading_run_id_as_single_token(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    payload = tmp_path / "review-panel-manifest.ndjson"
    payload.write_text("{}\n", encoding="utf-8")
    sibling = tmp_path / "panel-prompt-sizes.tsv"
    sibling.write_text("site\tslot\nreview\tcorrectness\n", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(
        argv: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, "LOG_WRITTEN=true\n", "")

    monkeypatch.setattr(review_tally.subprocess, "run", fake_run)

    rc = review_tally.log_phase(
        [
            "--run-id=-abc123",
            "--batch",
            "review-panel-manifest",
            "--action",
            "write",
            "--payload-file",
            str(payload),
            "--log-root",
            str(tmp_path / "logs"),
        ]
    )

    assert rc == 0
    assert len(calls) == 2
    for argv in calls:
        assert "--run-id=-abc123" in argv
        assert "--run-id" not in argv
    assert "--batch" in calls[0]
    assert calls[0][calls[0].index("--batch") + 1] == "review-panel-manifest"
    assert calls[1][calls[1].index("--batch") + 1] == "panel-prompt-sizes"


def test_log_phase_accepts_panel_prompt_sizes_batch(tmp_path: Path) -> None:
    payload = tmp_path / "panel-prompt-sizes.tsv"
    payload.write_text("site\tslot\nreview\tcorrectness\n", encoding="utf-8")

    result = run_review(
        "log-phase",
        "--run-id",
        "run-abc",
        "--batch",
        "panel-prompt-sizes",
        "--action",
        "write",
        "--payload-file",
        str(payload),
        "--log-root",
        str(tmp_path / "logs"),
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "logs" / "review" / "run-abc" / "panel-prompt-sizes.tsv").is_file()
# pyright: reportUnusedCallResult=false


def test_tally_code_votes_accumulates_public_oos_pool(tmp_path: Path) -> None:
    parent = tmp_path / "impl-parent"
    case = parent / "round-1"
    case.mkdir(parents=True)
    _ = (parent / "session-env.sh").write_text("", encoding="utf-8")
    _ = (case / "ballot.md").write_text(
        """### OOS_1: [OUT_OF_SCOPE] important follow-up
- **Reviewer**: Codex-Correctness
- **Severity**: important
- **Concern**: File this after aggregate evaluation.
""",
        encoding="utf-8",
    )
    for name in ("v1.txt", "v2.txt", "v3.txt"):
        _ = (case / name).write_text("OOS_1: NO SEVERITY=major\n", encoding="utf-8")

    result = run_review(
        "tally-code-votes",
        "--ballot-file",
        str(case / "ballot.md"),
        "--review-tmpdir",
        str(case),
        "--session-env-path",
        str(parent / "session-env.sh"),
        "--voter-files",
        str(case / "v1.txt"),
        str(case / "v2.txt"),
        str(case / "v3.txt"),
    )

    assert result.returncode == 0, result.stderr
    assert rts.kv_get(stdout=result.stdout, key="OOS_ACCEPTED_COUNT") == "0"
    pool = (parent / "oos-aggregate-pool.md").read_text(encoding="utf-8")
    assert "important follow-up" in pool
    assert "**Severity**: important" in pool
    assert not (parent / "oos-accepted-review.md").read_text(encoding="utf-8").strip()


def test_emit_tally_promotes_three_latent_pool_items_after_vote_rebuild(tmp_path: Path) -> None:
    parent = tmp_path / "impl-parent"
    case = parent / "round-1"
    case.mkdir(parents=True)
    _ = (parent / "session-env.sh").write_text("", encoding="utf-8")
    _ = (parent / "oos-aggregate-pool.md").write_text(
        """### FINDING_1: latent one
- **Severity**: latent
- **Concern**: one.

### FINDING_2: latent two
- **Severity**: latent
- **Concern**: two.

### FINDING_3: latent three
- **Severity**: latent
- **Concern**: three.
""",
        encoding="utf-8",
    )
    tally = case / "review-tally.env"
    _ = tally.write_text("ACCEPTED_COUNT=0\nREJECTED_COUNT=0\nNEUTRAL_COUNT=0\nOOS_ACCEPTED_COUNT=0\n", encoding="utf-8")
    accepted = case / "accepted-findings.md"
    _ = accepted.write_text("", encoding="utf-8")
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
        "--session-env-path",
        str(parent / "session-env.sh"),
        "--round",
        "1",
        "--mode",
        "diff",
    )

    assert result.returncode == 0, result.stderr
    assert "OOS_FILING_COUNT=3" in result.stdout
    local_sink = (case / "oos-accepted-review.md").read_text(encoding="utf-8")
    parent_sink = (parent / "oos-accepted-review.md").read_text(encoding="utf-8")
    assert local_sink.count("### OOS_") == 3
    assert "### FINDING_" not in local_sink
    assert parent_sink == local_sink
    assert "OOS_ACCEPTED_COUNT=0" in tally.read_text(encoding="utf-8")


def test_emit_tally_counts_main_agent_latents_toward_trigger(tmp_path: Path) -> None:
    parent = tmp_path / "impl-parent-main"
    case = parent / "round-1"
    case.mkdir(parents=True)
    _ = (parent / "session-env.sh").write_text("", encoding="utf-8")
    _ = (parent / "oos-aggregate-pool.md").write_text(
        """### FINDING_1: reviewer latent
- **Severity**: latent
- **Concern**: one.
""",
        encoding="utf-8",
    )
    _ = (parent / "oos-accepted-main-agent.md").write_text(
        """### OOS_1: main latent one
- **Severity**: latent
- **Concern**: two.

### OOS_2: main latent two
- **Severity**: latent
- **Concern**: three.
""",
        encoding="utf-8",
    )
    tally = case / "review-tally.env"
    _ = tally.write_text("ACCEPTED_COUNT=0\nREJECTED_COUNT=0\nNEUTRAL_COUNT=0\nOOS_ACCEPTED_COUNT=0\n", encoding="utf-8")
    accepted = case / "accepted-findings.md"
    _ = accepted.write_text("", encoding="utf-8")
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
        "--session-env-path",
        str(parent / "session-env.sh"),
        "--round",
        "1",
        "--mode",
        "diff",
    )

    assert result.returncode == 0, result.stderr
    assert "OOS_FILING_COUNT=1" in result.stdout
    assert "reviewer latent" in (case / "oos-accepted-review.md").read_text(encoding="utf-8")
