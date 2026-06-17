# pyright: reportMissingParameterType=false, reportUnknownParameterType=false
from __future__ import annotations

# pyright: reportUnusedCallResult=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportArgumentType=false

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import voting

CLI = Path(__file__).with_name("cli.py")


def run_cli(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def test_vote_thresholds_and_panel_labels() -> None:
    assert voting.accept_finding(2, 1, 0, 3)
    assert not voting.accept_finding(1, 2, 0, 3)
    assert voting.classify_result(1, 2, 0, 3) == "neutral"
    assert voting.classify_result(0, 3, 0, 3) == "rejected"
    assert voting.panel_tier(3) == "full-3"
    assert voting.panel_tier(2) == "unanimous-2"
    assert voting.panel_tier(1) == "single-judge"
    assert voting.panel_tier(0) == "main-agent-required"


def test_vote_for_id_last_match_and_exonerate(tmp_path: Path) -> None:
    voter = tmp_path / "voter.txt"
    voter.write_text(
        "FINDING_1: YES\n"
        "FINDING_10: YES\n"
        "finding_1: exonerate -- old token\n",
        encoding="utf-8",
    )
    result = run_cli("voting", "vote-for-id", "FINDING_1", str(voter))
    assert result.returncode == 0
    assert result.stdout == "NO\n"


def test_reviewer_security_and_split_ballot(tmp_path: Path) -> None:
    ballot = tmp_path / "ballot.md"
    ballot.write_text(
        "intro\n"
        "### FINDING_1: one\n- **Reviewer**: Structure\n- **Focus-Area**: security\n"
        "### OOS_2: two\nbody\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "blocks"
    result = run_cli("voting", "split-ballot", str(ballot), str(out_dir))
    assert result.returncode == 0
    assert (out_dir / "FINDING_1.md").exists()
    assert voting.reviewer_for_block(out_dir / "FINDING_1.md") == "Structure"
    assert voting.is_security_block(out_dir / "FINDING_1.md")

    dup = tmp_path / "dup.md"
    dup.write_text("### FINDING_1: one\n### FINDING_1: dup\n", encoding="utf-8")
    result = run_cli("voting", "split-ballot", str(dup), str(tmp_path / "dup-blocks"))
    assert result.returncode == 1
    assert "duplicate ballot heading FINDING_1" in result.stderr


@pytest.mark.parametrize(
    ("line", "expected_vote", "expected_correctness", "expected_uncertain"),
    [
        ("FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false -- QUALITY=weak", "YES", "true", "false"),
        ("FINDING_1: MAYBE CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false", "", "true", "false"),
        ("FINDING_1: EXONERATE CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false", "NO", "true", "false"),
        ("FINDING_1: YES CORRECTNESS=True SEVERITY=major QUALITY=good UNCERTAIN=false", "YES", "", "true"),
    ],
)
def test_parse_judge_vote_cases(
    tmp_path: Path,
    line: str,
    expected_vote: str,
    expected_correctness: str,
    expected_uncertain: str,
) -> None:
    voter = tmp_path / "voter.txt"
    voter.write_text(f"noise\n{line}\n", encoding="utf-8")
    result = run_cli("voting", "parse-judge-vote", str(voter), "FINDING_1")
    assert result.returncode == 0
    assert f"PARSED_VOTE={expected_vote}\n" in result.stdout
    assert f"PARSED_CORRECTNESS={expected_correctness}\n" in result.stdout
    assert f"PARSED_UNCERTAIN={expected_uncertain}\n" in result.stdout


def test_parse_judge_vote_missing_args_and_unreadable(tmp_path: Path) -> None:
    result = run_cli("voting", "parse-judge-vote")
    assert result.returncode == 2
    result = run_cli("voting", "parse-judge-vote", str(tmp_path / "missing.txt"), "FINDING_1")
    assert result.returncode == 2


def test_file_line_regex_and_false_positive() -> None:
    result = run_cli("voting", "file-line-regex", "--name", "extensionless-re")
    assert result.returncode == 0
    assert "Makefile" in result.stdout
    assert run_cli("voting", "false-positive-match", "Closed as duplicate of #123").returncode == 0
    assert run_cli("voting", "false-positive-match", "This is not a duplicate").returncode == 1


def test_ballot_parse_tally_vote_and_scoreboard(tmp_path: Path) -> None:
    ballot = tmp_path / "ballot.md"
    ballot.write_text(
        "### FINDING_1: Bug\n- **Concern**: first line\ncontinued\n"
        "### FINDING_2: [OOS] Drift\n- **Concern**: oos\n",
        encoding="utf-8",
    )
    parsed = run_cli("voting", "ballot-parse", "--ballot-file", str(ballot))
    assert "FINDING_1_CONCERN=first line continued" in parsed.stdout
    assert "FINDING_2_OOS=true" in parsed.stdout

    v1 = tmp_path / "v1.txt"
    v2 = tmp_path / "v2.txt"
    v1.write_text("FINDING_1: YES\nFINDING_2: NO\n", encoding="utf-8")
    v2.write_text("FINDING_1: YES\nFINDING_2: EXONERATE\n", encoding="utf-8")
    tally = run_cli("voting", "tally-vote", "--ballot-file", str(ballot), "--voter-files", str(v1), str(v2))
    assert "FINDING_1_ACCEPTED=true" in tally.stdout
    assert "FINDING_2_VOTES_NO=2" in tally.stdout

    tally_file = tmp_path / "tally.env"
    tally_file.write_text("REVIEWER=Structure ACCEPTED=true\n", encoding="utf-8")
    score_file = tmp_path / "score with spaces & metachar.md"
    score = run_cli(
        "voting",
        "scoreboard",
        "--tally-file",
        str(tally_file),
        "--reviewer-labels",
        "Structure, Testing",
        "--output-file",
        str(score_file),
    )
    assert "| Structure | 1 |" in score_file.read_text(encoding="utf-8")
    assert score.stdout == f"SCOREBOARD_FILE={voting.bash_printf_q(str(score_file))}\n"


def test_compose_tally_record_omits_code_review_body(tmp_path: Path) -> None:
    body = tmp_path / "body.md"
    body.write_text("# Code Review Voting Tally\nsecret body text\n", encoding="utf-8")
    result = run_cli(
        "voting",
        "compose-tally-record",
        "--phase",
        "code-review",
        "--mode",
        "hard",
        "--rounds",
        "2",
        "--accepted",
        "1",
        "--rejected",
        "3",
        "--body-file",
        str(body),
    )
    assert result.returncode == 0
    record = json.loads(result.stdout)
    assert record["batch"] == "code-review-tally"
    assert "body" not in record


def test_compose_tally_record_allows_code_review_self_review_mode() -> None:
    result = run_cli(
        "voting",
        "compose-tally-record",
        "--phase",
        "code-review",
        "--mode",
        "self-review",
        "--rounds",
        "1",
        "--accepted",
        "0",
        "--rejected",
        "0",
    )
    assert result.returncode == 0
    record = json.loads(result.stdout)
    assert record["batch"] == "code-review-tally"
    assert record["phase"] == "code-review"
    assert record["mode"] == "self-review"
    assert record["rounds"] == 1
    assert record["accepted_count"] == 0
    assert record["rejected_count"] == 0


def test_plan_review_rejects_self_review_mode(tmp_path: Path) -> None:
    body = tmp_path / "plan-body.md"
    body.write_text("Plan review body.\n", encoding="utf-8")
    result = run_cli(
        "voting",
        "compose-tally-record",
        "--phase",
        "plan-review",
        "--mode",
        "self-review",
        "--body-file",
        str(body),
    )
    assert result.returncode == 2


def _write_retry_launcher(root: Path, *, retry_output: str) -> None:
    py_dir = root / "python"
    py_dir.mkdir(parents=True)
    launcher = py_dir / "cli.py"
    launcher.write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "out = ''\n"
        "args = sys.argv[1:]\n"
        "i = 0\n"
        "while i < len(args):\n"
        "    if args[i] == '--output' and i + 1 < len(args):\n"
        "        out = args[i + 1]\n"
        "        i += 2\n"
        "    else:\n"
        "        i += 1\n"
        "Path(out).write_text(" + repr(retry_output + "\n") + ", encoding='utf-8')\n"
        "Path(out + '.done').write_text('0\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    launcher.chmod(0o755)
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    append = scripts / "append-tool-failure.sh"
    append.write_text("#!/usr/bin/env bash\nprintf 'append called\\n' >>\"$1\"\n", encoding="utf-8")
    append.chmod(0o755)


def test_parse_rate_retry_bare_status_and_oos_grammar(tmp_path: Path) -> None:
    root = tmp_path / "root"
    _write_retry_launcher(
        root,
        retry_output="OOS_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false",
    )
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### OOS_1: drift\n", encoding="utf-8")
    voter = tmp_path / "voter.txt"
    voter.write_text("narrative only\n", encoding="utf-8")
    prompt = tmp_path / "slot-prompt.txt"
    prompt.write_text("prompt\n", encoding="utf-8")
    result = run_cli(
        "voting",
        "parse-rate-retry",
        "--ballot-file",
        str(ballot),
        "--id-grammar",
        "finding-oos",
        "--review-tmpdir",
        str(tmp_path),
        "--plugin-root",
        str(root),
        "--dispatch-label",
        "agent dispatch-voters",
        "--retry-prefix-kind",
        "code",
        "--launch-mode",
        "description",
        "--ctx=--diff-file",
        "--ctx",
        "-leading-dash.diff",
        "--slot",
        "1",
        "--voter-file",
        str(voter),
        "--voter-tool",
        "codex",
        "--prompt-file",
        str(prompt),
    )
    assert result.returncode == 0
    assert result.stdout == "OK\n"
    assert "PARSE_RATE_STATUS" not in result.stdout
    assert voter.read_text(encoding="utf-8").startswith("OOS_1: YES")


def test_parse_rate_retry_claude_uses_agent_launcher_and_forwards_context(tmp_path: Path) -> None:
    root = tmp_path / "root"
    py_dir = root / "python"
    py_dir.mkdir(parents=True)
    argv_log = tmp_path / "claude-retry-argv.log"
    cli = py_dir / "cli.py"
    cli.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        f"Path({str(argv_log)!r}).write_text('\\n'.join(sys.argv[1:]), encoding='utf-8')\n"
        "out = sys.argv[sys.argv.index('--output') + 1]\n"
        "Path(out).write_text('FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\\n', encoding='utf-8')\n"
        "Path(out + '.done').write_text('0\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: bug\n", encoding="utf-8")
    voter = tmp_path / "claude-vote-output.txt"
    voter.write_text("narrative only\n", encoding="utf-8")
    prompt = tmp_path / "claude-vote-prompt.txt"
    prompt.write_text("prompt\n", encoding="utf-8")
    diff = tmp_path / "review.diff"
    plan = tmp_path / "plan.md"
    diff.write_text("diff", encoding="utf-8")
    plan.write_text("plan", encoding="utf-8")
    result = run_cli(
        "voting",
        "parse-rate-retry",
        "--ballot-file",
        str(ballot),
        "--id-grammar",
        "finding-only",
        "--review-tmpdir",
        str(tmp_path),
        "--plugin-root",
        str(root),
        "--dispatch-label",
        "agent dispatch-voters",
        "--retry-prefix-kind",
        "code",
        "--launch-mode",
        "description",
        "--ctx=--diff-file",
        "--ctx",
        str(diff),
        "--ctx=--plan-file",
        "--ctx",
        str(plan),
        "--slot",
        "1",
        "--voter-file",
        str(voter),
        "--voter-tool",
        "claude",
        "--prompt-file",
        str(prompt),
    )
    assert result.returncode == 0
    assert result.stdout == "OK\n"
    argv = argv_log.read_text(encoding="utf-8")
    assert "agent\nlaunch-claude-review" in argv
    assert "--diff-file" in argv
    assert str(diff) in argv
    assert "--plan-file" in argv
    assert str(plan) in argv
    assert voter.read_text(encoding="utf-8").startswith("FINDING_1: YES")


def test_parse_rate_failure_is_not_substantive_and_suppressed(tmp_path: Path) -> None:
    root = tmp_path / "root"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    launcher = scripts / "agent launch-review"
    launcher.write_text("#!/usr/bin/env bash\nexit 17\n", encoding="utf-8")
    launcher.chmod(0o755)
    append_log = tmp_path / "append.log"
    append = scripts / "append-tool-failure.sh"
    append.write_text(f"#!/usr/bin/env bash\nprintf called >>{append_log}\n", encoding="utf-8")
    append.chmod(0o755)
    base = tmp_path / "test-dispatch-code-voters.tmp"
    base.mkdir()
    ballot = base / "ballot.md"
    ballot.write_text("### FINDING_1: bug\n", encoding="utf-8")
    voter = base / "voter.txt"
    voter.write_text("narrative only\n", encoding="utf-8")
    prompt = base / "prompt.txt"
    prompt.write_text("prompt\n", encoding="utf-8")
    result = run_cli(
        "voting",
        "parse-rate-retry",
        "--voter-file",
        str(voter),
        "--voter-tool",
        "cursor",
        "--ballot-file",
        str(ballot),
        "--id-grammar",
        "finding-only",
        "--review-tmpdir",
        str(base),
        "--prompt-file",
        str(prompt),
        "--retry-prefix-kind",
        "plan",
        "--launch-mode",
        "description",
        "--plugin-root",
        str(root),
    )
    assert result.returncode == 0
    assert result.stdout == "NOT_SUBSTANTIVE\n"
    assert not append_log.exists()


def test_is_harness_review_path_matches_agent_voters_pytest_segment(tmp_path: Path) -> None:
    base = tmp_path / "test_agent_voters.tmp" / "review"
    voter = base / "voter.txt"
    assert voting.is_harness_review_path(base)
    assert voting.should_suppress_parse_rate_issue_append(voter, base)


def test_plan_coverage_and_degraded_warning(tmp_path: Path) -> None:
    good = tmp_path / "good.txt"
    empty = tmp_path / "empty.txt"
    good.write_text("vote\n", encoding="utf-8")
    empty.write_text("", encoding="utf-8")
    result = run_cli(
        "voting",
        "effective-judges",
        f"ok\t{good}\tOK",
        f"failed\t{good}\tOK",
        f"ok\t{good}\tNOT_SUBSTANTIVE",
        f"ok\t{empty}\tOK",
        "ok\t\tOK",
    )
    assert result.stdout == "1\n"
    result = run_cli("voting", "degraded-warning", "1", "3", "quota hit")
    assert result.returncode == 0
    assert result.stdout == "DEGRADED_PANEL_WARNING=**⚠ Degraded plan-review panel: 1/3 effective judges produced substantive vote output.** quota hit\n"
    assert "Degraded plan-review" in result.stderr


def test_voter_status_block_path_gate(tmp_path: Path) -> None:
    paths = tmp_path / "paths.txt"
    result = run_cli(
        "voting",
        "voter-status-block",
        "p1",
        "Claude",
        "ok",
        "OK",
        "p2",
        "Codex",
        "skipped",
        "SKIPPED",
        "p3",
        "Cursor",
        "failed",
        "SKIPPED",
        str(paths),
    )
    assert "VOTER_PATHS_FILE" not in result.stdout
    paths.write_text("p1\n", encoding="utf-8")
    result = run_cli(
        "voting",
        "voter-status-block",
        "p1",
        "Claude",
        "ok",
        "OK",
        "p2",
        "Codex",
        "skipped",
        "SKIPPED",
        "p3",
        "Cursor",
        "failed",
        "SKIPPED",
        str(paths),
    )
    assert f"VOTER_PATHS_FILE={paths}\n" in result.stdout


def test_lint_focus_area_enum_passes() -> None:
    result = run_cli("lint", "focus-area-enum")
    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


def _write_tally_logger(tmp_path: Path) -> Path:
    logger = tmp_path / "stub-larch-log.sh"
    logger.write_text("#!/usr/bin/env bash\nprintf 'LOG_WRITTEN=true\\n'\n", encoding="utf-8")
    logger.chmod(0o755)
    return logger


def test_write_tally_header_validation_and_logger_kv_reemission(tmp_path: Path) -> None:
    invalid_body = tmp_path / "invalid-body.md"
    invalid_body.write_text("## Voting Tally\n## Foo\n", encoding="utf-8")
    result = run_cli(
        "voting",
        "write-tally",
        "--log-root",
        str(tmp_path / "logs-invalid"),
        "--skill",
        "implement",
        "--run-id",
        "run-code-invalid",
        "--phase",
        "code-review",
        "--mode",
        "simple",
        "--body-file",
        str(invalid_body),
    )
    assert result.returncode == 2
    assert "unrecognized section header in code-review body: ## Foo" in result.stderr
    assert result.stdout == ""

    logger = _write_tally_logger(tmp_path)
    valid_rejected_round_body = tmp_path / "valid-rejected-round-body.md"
    valid_rejected_round_body.write_text(
        "# Rejected Findings\n\n# Review Round 2\n\n### FINDING_1: valid rejected finding\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["LARCH_WRITE_TALLY_LOGGER"] = str(logger)
    result = run_cli(
        "voting",
        "write-tally",
        "--log-root",
        str(tmp_path / "logs-code-round"),
        "--skill",
        "implement",
        "--run-id",
        "run-code-round",
        "--phase",
        "code-review",
        "--mode",
        "simple",
        "--accepted",
        "1",
        "--rejected",
        "0",
        "--body-file",
        str(valid_rejected_round_body),
        env=env,
    )
    assert result.returncode == 0

    valid_body = tmp_path / "valid-body.md"
    valid_body.write_text("# Code Review Voting Tally\n", encoding="utf-8")
    result = run_cli(
        "voting",
        "write-tally",
        "--log-root",
        str(tmp_path / "logs-code"),
        "--skill",
        "implement",
        "--run-id",
        "run-code",
        "--phase",
        "code-review",
        "--mode",
        "simple",
        "--accepted",
        "0",
        "--rejected",
        "1",
        "--body-file",
        str(valid_body),
        env=env,
    )
    assert result.returncode == 0
    assert "LOG_WRITTEN=true" in result.stdout

    plan_body = tmp_path / "plan-body.md"
    plan_body.write_text("Plan review accepted with one follow-up.\n", encoding="utf-8")
    result = run_cli(
        "voting",
        "write-tally",
        "--log-root",
        str(tmp_path / "logs-plan"),
        "--skill",
        "implement",
        "--run-id",
        "run-plan",
        "--phase",
        "plan-review",
        "--mode",
        "hard",
        "--rounds",
        "3",
        "--accepted",
        "2",
        "--rejected",
        "1",
        "--body-file",
        str(plan_body),
        env=env,
    )
    assert result.returncode == 0
    assert "LOG_WRITTEN=true" in result.stdout


def test_parse_rate_retry_empty_retry_output_stays_not_substantive(tmp_path: Path) -> None:
    root = tmp_path / "root"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    launcher = scripts / "agent launch-review"
    launcher.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "out=''\n"
        "while [ $# -gt 0 ]; do\n"
        '  case "$1" in --output) out="$2"; shift 2 ;; *) shift ;; esac\n'
        "done\n"
        ': >"$out"\n'
        'printf "0\\n" >"$out.done"\n',
        encoding="utf-8",
    )
    launcher.chmod(0o755)
    append = scripts / "append-tool-failure.sh"
    append.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    append.chmod(0o755)
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: bug\n", encoding="utf-8")
    voter = tmp_path / "voter.txt"
    voter.write_text("narrative only\n", encoding="utf-8")
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("prompt\n", encoding="utf-8")
    result = run_cli(
        "voting",
        "parse-rate-retry",
        "--ballot-file",
        str(ballot),
        "--id-grammar",
        "finding-only",
        "--review-tmpdir",
        str(tmp_path),
        "--plugin-root",
        str(root),
        "--dispatch-label",
        "agent dispatch-voters",
        "--retry-prefix-kind",
        "code",
        "--launch-mode",
        "description",
        "--slot",
        "1",
        "--voter-file",
        str(voter),
        "--voter-tool",
        "claude",
        "--prompt-file",
        str(prompt),
    )
    assert result.returncode == 0
    assert result.stdout == "NOT_SUBSTANTIVE\n"
    assert voter.read_text(encoding="utf-8") == "narrative only\n"


def test_quiet_parent_diagnostic_stays_off_stdout(tmp_path: Path) -> None:
    ballot = tmp_path / "ballot.md"
    voter = tmp_path / "voter.txt"
    ballot.write_text("### FINDING_1: bug\n", encoding="utf-8")
    voter.write_text("narrative\n", encoding="utf-8")
    env = os.environ.copy()
    env.pop("LARCH_QUIET_DISABLE", None)
    env["LARCH_QUIET_ACTIVE"] = "1"
    env["LARCH_QUIET_PID"] = "999999"
    result = run_cli(
        "voting",
        "parse-rate-check",
        "--voter-file",
        str(voter),
        "--voter-tool",
        "claude",
        "--ballot-file",
        str(ballot),
        "--id-grammar",
        "finding-only",
        "--review-tmpdir",
        str(tmp_path),
        env=env,
    )
    assert result.returncode == 0
    assert result.stdout == "PARSE_RATE_STATUS=NOT_SUBSTANTIVE\n"
    assert "Voter claude" in result.stderr


def test_findings_classification_header_cli(capsys) -> None:
    rc = voting.findings_classification_header_main([])
    assert rc == 0
    assert capsys.readouterr().out == voting.FINDINGS_CLASSIFICATION_HEADER + "\n"
