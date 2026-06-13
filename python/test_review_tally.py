from __future__ import annotations

import os
import subprocess
from pathlib import Path

import review_test_support as rts

ROOT = rts.ROOT
CLI = rts.CLI


def run_review(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return rts.run_review(*args, env=env)


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

### FINDING_2: **Important** — `correctness` — `scripts/dispatch-code-voters.sh:42`
- **Reviewer**: Codex-Structure
- **Concern**: Null check missing on return path.
- **Suggested revision**: Add nil guard.
""",
        encoding="utf-8",
    )
    _ = (case / "scope-files.txt").write_text("scripts/dispatch-code-voters.sh\n", encoding="utf-8")
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
    _ = (case / "scope-files.txt").write_text("scripts/dispatch-code-voters.sh\n", encoding="utf-8")
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
