# pyright: reportMissingParameterType=false, reportUnknownParameterType=false
from __future__ import annotations

# pyright: reportUnusedCallResult=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportArgumentType=false

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import cast

import pytest

from larch.review import voting
from larch.core import config
from larch.review.review_types import JudgeSeverity, ReviewVote

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
    assert voting.accept_finding(yes=2, no=1, exonerate=0, eligible=3)
    assert not voting.accept_finding(yes=1, no=2, exonerate=0, eligible=3)
    assert voting.classify_result(yes=1, no=2, exonerate=0, eligible=3) == "neutral"
    assert voting.classify_result(yes=0, no=3, exonerate=0, eligible=3) == "rejected"
    assert voting.panel_tier(3) == "full-3"
    assert voting.panel_tier(2) == "unanimous-2"
    assert voting.panel_tier(1) == "single-judge"
    assert voting.panel_tier(0) == "main-agent-required"


def test_normalize_reviewer_basename_strips_path_and_waterfall_suffixes() -> None:
    assert voting.normalize_reviewer_basename("structure.txt") == "structure.txt"
    assert voting.normalize_reviewer_basename("out/dir/correctness-phase2.txt") == "correctness.txt"
    assert voting.normalize_reviewer_basename("security-phase2-retry.txt") == "security.txt"
    assert voting.normalize_reviewer_basename("edge-cases-phase3") == "edge-cases"
    assert voting.normalize_reviewer_basename("plain") == "plain"


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
    "text",
    [
        "### FINDING_1: one\nThe affected block uses focus-area=security metadata.\n",
        "### FINDING_1: one\n- **Focus-Area**: security\n",
        "### OOS_1: Some finding\n- **Focus area**: security\n",
    ],
)
def test_is_security_block_text_focus_area_forms(text: str) -> None:
    assert voting.is_security_block_text(text)


def test_is_security_block_text_non_security_returns_false() -> None:
    assert not voting.is_security_block_text(
        "### OOS_1: Some finding\n"
        "- **Description**: something\n"
        "- **Focus area**: correctness\n"
    )


def test_is_security_block_space_separated_focus_area(tmp_path: Path) -> None:
    # The accepted OOS template writes "- **Focus area**: security" (space, bold).
    # The detector must match this form in addition to hyphenated "focus-area".
    block = tmp_path / "OOS_1.md"
    block.write_text(
        "### OOS_1: Some finding\n"
        "- **Description**: something\n"
        "- **Reviewer**: edge-cases\n"
        "- **Severity**: major\n"
        "- **Focus area**: security\n"
        "- **Location**: python/foo.py:10\n",
        encoding="utf-8",
    )
    assert voting.is_security_block(block)


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


def test_markdown_table_votes_are_recovered(tmp_path: Path) -> None:
    # Issue #5078: a voter that emits a markdown table instead of anchored
    # FINDING_N: lines must still have its votes parsed and counted, not dropped
    # from quorum as JUDGE_ERROR.
    voter = tmp_path / "voter.txt"
    voter.write_text(
        "| Item | Vote | Key reason |\n"
        "|------|------|------------|\n"
        "| FINDING_1 | **YES** | clear win |\n"
        "| FINDING_2 | NO | not convinced |\n"
        "| OOS_1 | EXONERATE | out of scope |\n",
        encoding="utf-8",
    )
    assert voting.vote_for_id(ballot_id="FINDING_1", voter_file=voter) == "YES"
    assert voting.vote_for_id(ballot_id="FINDING_2", voter_file=voter) == "NO"
    assert voting.vote_for_id(ballot_id="OOS_1", voter_file=voter) == "NO"  # EXONERATE maps to NO
    assert voting.parse_judge_vote(voter_file=voter, ballot_id="FINDING_1")[0] == "YES"

    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: a\n### FINDING_2: b\n", encoding="utf-8")
    # The parse-rate gate must see the recovered votes and keep the voter (OK, not NOT_SUBSTANTIVE).
    assert (
        voting.check_voter_parse_rate(
            voter_file=str(voter),
            voter_tool="claude",
            ballot_file=str(ballot),
            id_grammar="finding-oos",
            review_tmpdir=str(tmp_path),
            log_mode="quiet",
        )
        == "OK"
    )


def test_markdown_table_votes_preserve_axis_tokens(tmp_path: Path) -> None:
    voter = tmp_path / "voter.txt"
    voter.write_text(
        "| FINDING_1 | YES | CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false | clear win |\n",
        encoding="utf-8",
    )
    vote, correctness, severity, quality, uncertain = voting.parse_judge_vote(voter_file=voter, ballot_id="FINDING_1")
    assert vote == "YES"
    assert correctness == "true"
    assert severity == "major"
    assert quality == "good"
    assert uncertain == "false"


def test_anchored_votes_unaffected_by_markdown_normalization(tmp_path: Path) -> None:
    # Plain anchored votes (no pipe characters) pass through unchanged.
    voter = tmp_path / "voter.txt"
    voter.write_text("FINDING_1: YES\nFINDING_2: NO -- reason\n", encoding="utf-8")
    assert voting.vote_for_id(ballot_id="FINDING_1", voter_file=voter) == "YES"
    assert voting.vote_for_id(ballot_id="FINDING_2", voter_file=voter) == "NO"


def test_file_line_regex_and_false_positive() -> None:
    result = run_cli("voting", "file-line-regex", "--name", "extensionless-re")
    assert result.returncode == 0
    assert "Makefile" in result.stdout
    assert run_cli("voting", "false-positive-match", "Closed as duplicate of #123").returncode == 0
    assert run_cli("voting", "false-positive-match", "This is not a duplicate").returncode == 1


def test_classification_row_panel_inputs_keep_raw_header_and_oos_scope() -> None:
    text = (
        voting.CODE_REVIEW_FINDINGS_CLASSIFICATION_HEADER
        + "\nFINDING_1\tcodex|cursor\taccepted\tYES\ttrue\tmajor\tgood\tfalse\tcodex\tNO\ttrue\tminor\tgood\tfalse\tcursor\tYES\ttrue\tminor\tgood\tfalse\tclaude\toos\n"
    )
    rows = voting.classification_row_panel_inputs(text, panel_kind="code-review")
    assert rows[0].raw_row["finding_id"] == "FINDING_1"
    assert "scope" in rows[0].header
    assert rows[0].reviewer_column == "reviewer_slots"
    assert rows[0].voter_votes[0] == ("codex", "YES")
    assert voting.classification_row_is_oos(rows[0].raw_row, header=rows[0].header)
    agreement = voting.voter_agreement_row_from_panel(
        voting_result=rows[0].raw_row["voting_result"],
        voter_votes=rows[0].voter_votes,
        panel=rows[0].panel,
        voter_severities=rows[0].voter_severities,
    )
    assert agreement is not None


def test_classification_row_panel_inputs_design_labels_match_agreement_parser() -> None:
    text = (
        voting.FINDINGS_CLASSIFICATION_HEADER
        + "\nFINDING_1\tarchitect\taccepted\tYES\ttrue\tmajor\tgood\tfalse\t\tNO\ttrue\tminor\tgood\tfalse\t\tYES\ttrue\tminor\tgood\tfalse\t\tmajor\tin_scope\n"
    )
    prep = voting.classification_row_panel_inputs(text, panel_kind="design")[0]
    parsed = voting.voter_agreement_rows_from_tsv(text, panel_kind="design").rows[0]
    assert [label for label, _vote in prep.voter_votes] == ["Claude", "Codex", "Cursor"]
    assert parsed["voters"][0]["voter"] == "Claude"  # type: ignore[reportIndexIssue]


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


def test_parse_rate_retry_bare_status_and_oos_grammar(tmp_path: Path) -> None:
    root = tmp_path / "root"
    (root / "python").mkdir(parents=True)
    (root / "python" / "cli.py").write_text("# unused\n", encoding="utf-8")
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
    assert result.stdout == "NOT_SUBSTANTIVE\n"
    assert "PARSE_RATE_STATUS" not in result.stdout
    assert voter.read_text(encoding="utf-8") == "narrative only\n"
    assert not (tmp_path / "voter-parse-retry.txt").exists()


def test_voter_agreement_row_from_panel_semantics() -> None:
    accepted = voting.voter_agreement_row_from_panel(
        voting_result="accepted",
        voter_votes=[("Claude", "YES"), ("Codex", "NO"), ("Cursor", "JUDGE_ERROR")],
        voter_severities=["major", "nit", ""],
        panel="design",
    )
    assert accepted is not None
    accepted_voters = cast("list[dict[str, object]]", accepted["voters"])
    assert [voter["severity"] for voter in accepted_voters] == ["major", "nit", ""]
    records = voting.compute_voter_agreement([accepted], min_votes=1)
    by_voter = {str(record["voter"]): record for record in records}
    assert by_voter["Claude"]["agree"] == 1
    assert by_voter["Codex"]["disagree"] == 1
    assert by_voter["Cursor"]["missing"] == 1
    assert by_voter["Cursor"]["eligible"] == 0

    rejected = voting.voter_agreement_row_from_panel(
        voting_result="rejected",
        voter_votes=[("Claude", "NO"), ("Codex", "YES")],
        panel="design",
    )
    assert rejected is not None
    records = voting.compute_voter_agreement([rejected], min_votes=1)
    by_voter = {str(record["voter"]): record for record in records}
    assert by_voter["Claude"]["agree"] == 1
    assert by_voter["Codex"]["disagree"] == 1

    assert voting.voter_agreement_row_from_panel(
        voting_result="neutral",
        voter_votes=[("Claude", "YES"), ("Codex", "NO")],
    ) is None
    assert voting.voter_agreement_row_from_panel(
        voting_result="accepted",
        voter_votes=[("Claude", "YES"), ("Codex", "")],
    ) is None
    assert voting.voter_agreement_row_from_panel(
        voting_result="accepted",
        voter_votes=[],
        voter_severities=None,
    ) is None
    with pytest.raises(ValueError, match="voter_severities"):
        voting.voter_agreement_row_from_panel(
            voting_result="accepted",
            voter_votes=[("Claude", "YES"), ("Codex", "NO")],
            voter_severities=["major"],
        )


def test_voter_agreement_rows_from_tsv_schema_shapes() -> None:
    design_header = voting.findings_classification_header()
    design22 = (
        design_header
        + "\nFINDING_1\tR\taccepted\tYES\t\tmajor\t\t\tClaude\tNO\t\tnit\t\t\tCodex\tYES\t\tuncertain\t\t\tCursor\tmajor\n"
    )
    design_rows = voting.voter_agreement_rows_from_tsv(design22, panel_kind="design").rows
    assert len(design_rows) == 1
    design_voters = cast("list[dict[str, object]]", design_rows[0]["voters"])
    assert [voter["voter"] for voter in design_voters] == ["Claude", "Codex", "Cursor"]
    assert [voter["severity"] for voter in design_voters] == ["major", "nit", "uncertain"]

    design21_header = design_header.removesuffix("\tbody_severity")
    design21 = (
        design21_header
        + "\nFINDING_2\tR\trejected\tNO\t\t\t\t\tClaude\tYES\t\t\t\t\tCodex\tNO\t\t\t\t\tCursor\n"
    )
    design21_rows = voting.voter_agreement_rows_from_tsv(design21, panel_kind="design").rows
    assert len(design21_rows) == 1
    design21_voters = cast("list[dict[str, object]]", design21_rows[0]["voters"])
    assert [voter["voter"] for voter in design21_voters] == ["Claude", "Codex", "Cursor"]
    assert [voter["severity"] for voter in design21_voters] == ["", "", ""]

    code21 = (
        voting.code_review_classification_header()
        + "\nFINDING_1\tR\taccepted\tYES\t\tblocker\t\t\tcursor-validity\tNO\t\tminor\t\t\tcursor-plan-fidelity\tYES\t\tmajor\t\t\tcursor-pragmatism\n"
    )
    code_rows = voting.voter_agreement_rows_from_tsv(code21, panel_kind="code-review").rows
    code_voters = cast("list[dict[str, object]]", code_rows[0]["voters"])
    assert [voter["voter"] for voter in code_voters] == [
        "cursor-validity",
        "cursor-plan-fidelity",
        "cursor-pragmatism",
    ]
    assert [voter["severity"] for voter in code_voters] == ["blocker", "minor", "major"]

    compact = (
        "finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\t"
        "v2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain\n"
        "FINDING_1\tR\taccepted\tNO\t\t\t\t\tYES\t\t\t\t\tYES\t\t\t\t\n"
    )
    compact_rows = voting.voter_agreement_rows_from_tsv(compact, panel_kind="code-review").rows
    compact_voters = cast("list[dict[str, object]]", compact_rows[0]["voters"])
    assert [voter["voter"] for voter in compact_voters] == ["v1", "v2", "v3"]
    assert [voter["severity"] for voter in compact_voters] == ["", "", ""]

    code21_severity_only_header = voting.code_review_classification_header().replace("\tv1_tool", "").replace("\tv2_tool", "").replace("\tv3_tool", "")
    code21_severity_only = (
        code21_severity_only_header
        + "\nFINDING_1\tR\taccepted\tYES\t\t\t\t\tNO\t\t\t\t\tYES\t\t\t\t\n"
    )
    severity_only_rows = voting.voter_agreement_rows_from_tsv(code21_severity_only, panel_kind="code-review").rows
    severity_only_voters = cast("list[dict[str, object]]", severity_only_rows[0]["voters"])
    assert [voter["voter"] for voter in severity_only_voters] == ["v1", "v2", "v3"]


def test_compute_voter_severity_distribution_yes_votes_only() -> None:
    rows = [
        voting.voter_agreement_row_from_panel(
            voting_result="accepted",
            voter_votes=[("v1", vote), ("v2", "NO"), ("v3", "YES")],
            voter_severities=[severity, "blocker", "major"],
            panel="code-review",
        )
        for vote, severity in [
            *[("YES", "blocker") for _ in range(9)],
            ("YES", "uncertain"),
            ("YES", ""),
            ("YES", "bogus"),
            ("NO", "major"),
        ]
    ]
    eligible_rows = [row for row in rows if row is not None]
    records = voting.compute_voter_severity_distribution(eligible_rows)
    v1 = next(record for record in records if record["voter"] == "v1")
    assert v1["yes_votes"] == 12
    assert v1["blocker"] == 9
    assert v1["major"] == 0
    assert v1["uncertain"] == 1
    assert v1["missing_severity"] == 2
    assert v1["valid_yes_severity_count"] == 10
    assert v1["high_rate"] == 0.9
    assert v1["calibration_score"] == 1.0
    assert v1["uncalibrated"] is False

    custom = voting.compute_voter_severity_distribution(
        eligible_rows,
        high_severity_threshold=0.50,
    )
    custom_v1 = next(record for record in custom if record["voter"] == "v1")
    assert custom_v1["uncalibrated"] is True
    assert custom_v1["calibration_score"] == pytest.approx(0.2)

    v2 = next(record for record in records if record["voter"] == "v2")
    assert v2["yes_votes"] == 0
    assert v2["high_rate"] is None
    assert v2["calibration_score"] is None
    assert v2["uncalibrated"] is False

    v3 = next(record for record in records if record["voter"] == "v3")
    assert v3["high_rate"] == 1.0
    assert float(v3["calibration_score"]) < float(v1["calibration_score"])

    threshold_edge = voting.compute_voter_severity_distribution(
        eligible_rows,
        high_severity_threshold=1.0,
    )
    edge_v3 = next(record for record in threshold_edge if record["voter"] == "v3")
    assert edge_v3["calibration_score"] == 1.0
    assert edge_v3["uncalibrated"] is False


def test_render_voter_severity_scoreboard_empty() -> None:
    rendered = voting.render_voter_severity_scoreboard([])
    assert "## Voter Severity Scoreboard" in rendered
    assert "Calibration Score" in rendered
    assert "| undefined | n/a | 0 | 0 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | false |" in rendered


def test_render_voter_severity_scoreboard_calibration_score() -> None:
    rendered = voting.render_voter_severity_scoreboard([
        {
            "panel": "code-review",
            "voter": "mixed",
            "yes_votes": 10,
            "blocker": 0,
            "major": 9,
            "minor": 0,
            "nit": 0,
            "uncertain": 1,
            "missing_severity": 0,
            "high_rate": 0.9,
            "calibration_score": 1.0,
            "uncalibrated": False,
        },
        {
            "panel": "code-review",
            "voter": "all-high",
            "yes_votes": 10,
            "blocker": 0,
            "major": 10,
            "minor": 0,
            "nit": 0,
            "uncertain": 0,
            "missing_severity": 0,
            "high_rate": 1.0,
            "calibration_score": 0.0,
            "uncalibrated": True,
        },
    ])
    assert "| code-review | mixed | 10 | 0 | 9 | 0 | 0 | 1 | 0 | 0.900 | 1.000 | false |" in rendered
    assert "| code-review | all-high | 10 | 0 | 10 | 0 | 0 | 0 | 0 | 1.000 | 0.000 | true |" in rendered


def test_compute_voter_agreement_outlier_threshold() -> None:
    low_sample = [
        voting.voter_agreement_row_from_panel(
            voting_result="accepted",
            voter_votes=[("v1", "NO"), ("v2", "YES")],
            panel="code-review",
        )
    ]
    records = voting.compute_voter_agreement([row for row in low_sample if row is not None], min_votes=2)
    assert next(record for record in records if record["voter"] == "v1")["outlier"] is False

    rows = [
        voting.voter_agreement_row_from_panel(
            voting_result="accepted",
            voter_votes=[("v1", "NO"), ("v2", "YES")],
            panel="code-review",
        )
        for _ in range(2)
    ]
    records = voting.compute_voter_agreement([row for row in rows if row is not None], min_votes=2)
    assert next(record for record in records if record["voter"] == "v1")["outlier"] is True

    mixed = [
        voting.voter_agreement_row_from_panel(
            voting_result="accepted",
            voter_votes=[("v1", vote), ("v2", "YES")],
            panel="code-review",
        )
        for vote in ("YES", "NO")
    ]
    records = voting.compute_voter_agreement([row for row in mixed if row is not None], min_votes=2)
    v1 = next(record for record in records if record["voter"] == "v1")
    assert v1["agreement_rate"] == 0.5
    assert v1["outlier"] is False


def test_voter_agreement_tsv_and_panel_parity() -> None:
    tsv = (
        voting.findings_classification_header()
        + "\nFINDING_1\tR\taccepted\tYES\t\t\t\t\tClaude\tNO\t\t\t\t\tCodex\tYES\t\t\t\t\tCursor\tmajor\n"
        + "FINDING_2\tR\trejected\tNO\t\t\t\t\tClaude\tYES\t\t\t\t\tCodex\tNO\t\t\t\t\tCursor\tminor\n"
    )
    from_tsv = voting.voter_agreement_rows_from_tsv(tsv, panel_kind="design").rows
    from_panel = [
        row
        for row in [
            voting.voter_agreement_row_from_panel(
                voting_result="accepted",
                voter_votes=[("Claude", "YES"), ("Codex", "NO"), ("Cursor", "YES")],
                panel="design",
            ),
            voting.voter_agreement_row_from_panel(
                voting_result="rejected",
                voter_votes=[("Claude", "NO"), ("Codex", "YES"), ("Cursor", "NO")],
                panel="design",
            ),
        ]
        if row is not None
    ]
    assert voting.compute_voter_agreement(from_tsv) == voting.compute_voter_agreement(from_panel)


def test_normalize_vote_cell_maps_exonerate_to_no() -> None:
    tsv = (
        voting.findings_classification_header()
        + "\nFINDING_1\tR\trejected\tEXONERATE\t\t\t\t\tClaude\tYES\t\t\t\t\tCodex\tNO\t\t\t\t\tCursor\tmajor\n"
    )
    rows = voting.voter_agreement_rows_from_tsv(tsv, panel_kind="design").rows
    assert len(rows) == 1
    voters = cast("list[dict[str, object]]", rows[0]["voters"])
    claude = next(voter for voter in voters if voter["voter"] == "Claude")
    assert claude["vote"] == "NO"
    assert claude["agree"] == 1
    records = voting.compute_voter_agreement(rows, min_votes=1)
    assert next(record for record in records if record["voter"] == "Claude")["agree"] == 1


def test_classification_tsv_schema_supported() -> None:
    design_header = voting.findings_classification_header()
    code_header = voting.code_review_classification_header()
    assert voting.classification_tsv_schema_supported(
        design_header + "\n", panel_kind="design"
    )
    assert not voting.classification_tsv_schema_supported(
        code_header + "\n", panel_kind="design"
    )
    assert voting.classification_tsv_schema_supported(
        code_header + "\n", panel_kind="code-review"
    )
    assert not voting.classification_tsv_schema_supported(
        design_header + "\n", panel_kind="code-review"
    )
    assert not voting.classification_tsv_schema_supported(
        "finding_id\treviewer_slots\tvoting_result\tjudge1_vote\n",
        panel_kind="code-review",
    )
    assert not voting.classification_tsv_schema_supported(
        "finding_id\tfinding_reviewers\tvoting_result\n",
        panel_kind="design",
    )


def test_parse_rate_retry_classify_only_dispatch_shaped_argv(tmp_path: Path) -> None:
    root = tmp_path / "root"
    (root / "python").mkdir(parents=True)
    (root / "python" / "cli.py").write_text("# unused\n", encoding="utf-8")
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: bug\n", encoding="utf-8")
    voter = tmp_path / "claude-vote-output.txt"
    voter.write_text("narrative only\n", encoding="utf-8")
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
    )
    assert result.returncode == 0
    assert result.stdout == "NOT_SUBSTANTIVE\n"
    assert voter.read_text(encoding="utf-8") == "narrative only\n"
    assert not (tmp_path / "claude-vote-output-parse-retry.txt").exists()
    assert not (tmp_path / "claude-vote-output-first-pass.txt").exists()


def test_parse_rate_retry_legacy_argv_is_classify_only(tmp_path: Path) -> None:
    root = tmp_path / "root"
    (root / "python").mkdir(parents=True)
    (root / "python" / "cli.py").write_text("# unused\n", encoding="utf-8")
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: bug\n", encoding="utf-8")
    voter = tmp_path / "cursor-vote-output.txt"
    voter.write_text("narrative only\n", encoding="utf-8")
    prompt = tmp_path / "cursor-vote-prompt.txt"
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
        "3",
        "--voter-file",
        str(voter),
        "--voter-tool",
        "cursor",
        "--prompt-file",
        str(prompt),
    )
    assert result.returncode == 0
    assert result.stdout == "NOT_SUBSTANTIVE\n"
    assert voter.read_text(encoding="utf-8") == "narrative only\n"
    assert not (tmp_path / "cursor-vote-output-parse-retry.txt").exists()
    assert not (tmp_path / "cursor-vote-output-first-pass.txt").exists()


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
        "--plugin-root",
        str(root),
    )
    assert result.returncode == 0
    assert result.stdout == "NOT_SUBSTANTIVE\n"
    assert not append_log.exists()


def test_judge_error_parse_threshold_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    # Issue #4880: the per-voter JUDGE_ERROR parse-rate threshold is tunable via env (default 0.8).
    monkeypatch.delenv("LARCH_VOTER_JUDGE_ERROR_PARSE_THRESHOLD", raising=False)
    assert voting._judge_error_parse_threshold() == 0.8  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setenv("LARCH_VOTER_JUDGE_ERROR_PARSE_THRESHOLD", "0.5")
    assert voting._judge_error_parse_threshold() == 0.5  # pyright: ignore[reportPrivateUsage]
    # Invalid, empty, or out-of-range values fall back to the default.
    for bad in ("abc", "0", "-0.1", "1.5", ""):
        monkeypatch.setenv("LARCH_VOTER_JUDGE_ERROR_PARSE_THRESHOLD", bad)
        assert voting._judge_error_parse_threshold() == 0.8  # pyright: ignore[reportPrivateUsage]


def test_parse_rate_diag_uses_bounded_prefix_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: bug\n### FINDING_2: bug\n", encoding="utf-8")
    voter = tmp_path / "voter.txt"
    voter.write_text("X" * 1000, encoding="utf-8")

    def forbidden_read_bytes(_path: Path) -> bytes:
        raise AssertionError("read_bytes should not be used for parse-rate snippets")

    monkeypatch.setattr(Path, "read_bytes", forbidden_read_bytes)
    assert (
        voting.check_voter_parse_rate(
            voter_file=str(voter),
            voter_tool="cursor",
            ballot_file=str(ballot),
            id_grammar="finding-only",
            review_tmpdir=str(tmp_path),
            log_mode="quiet",
        )
        == "NOT_SUBSTANTIVE"
    )
    diag = (tmp_path / "voter-parse-rate-diag.txt").read_text(encoding="utf-8")
    assert "--- first 200 bytes of voter output ---\n" + ("X" * 200) in diag
    assert "X" * 201 not in diag


def test_is_harness_review_path_matches_agent_voters_pytest_segment(tmp_path: Path) -> None:
    base = tmp_path / "test_agent_voters.tmp" / "review"
    voter = base / "voter.txt"
    assert voting.is_harness_review_path(base)
    assert voting.should_suppress_parse_rate_issue_append(voter_path=voter, base_tmp=base)


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
    assert result.returncode == 0
    assert "WARNING=code-review body header validation ignored" in result.stderr
    assert "unrecognized section header: ## Foo" in result.stderr
    assert "unrecognized section header" not in result.stdout
    assert "LOG_WRITTEN=true" in result.stdout
    assert all("=" in line for line in result.stdout.splitlines())
    record_path = tmp_path / "logs-invalid" / "implement" / "run-code-invalid" / "code-review-tally.json"
    assert record_path.is_file()
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["schema_version"] == 2
    assert record["phase"] == "code-review"
    assert record["batch"] == "code-review-tally"
    assert "body" not in record

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
    assert result.stderr == ""

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
    assert result.stderr == ""
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
    plan_record_path = tmp_path / "logs-plan" / "implement" / "run-plan" / "plan-review-tally.json"
    plan_record = json.loads(plan_record_path.read_text(encoding="utf-8"))
    assert plan_record["body"] == "Plan review accepted with one follow-up.\n"


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


def test_code_review_classification_header_is_22_column_schema() -> None:
    code = voting.code_review_classification_header().split("\t")
    design = voting.findings_classification_header().split("\t")
    assert len(code) == 22
    assert code[1] == "reviewer_slots"
    assert "body_severity" not in code
    assert code[8] == "v1_tool"
    assert code[14] == "v2_tool"
    assert code[20] == "v3_tool"
    assert code[-1] == "scope"
    assert len(design) == 23
    assert design[1] == "finding_reviewers"
    assert design[-1] == "scope"
    assert design[-2] == "body_severity"


def test_weighted_finding_points_and_attribution_helpers() -> None:
    assert voting.accepted_finding_points_from_severities(["major"]) == 2
    assert voting.accepted_finding_points_from_severities(["major", "blocker"]) == 2
    assert voting.accepted_finding_points_from_severities(["major", "blocker"], votes=["YES", "YES"]) == 2
    assert voting.accepted_finding_points_from_severities(["major", "minor"], votes=["YES", "YES"]) == 1
    assert voting.accepted_finding_points_from_severities(["major", "minor", "minor"], votes=["YES", "YES", "YES"]) == 1
    assert voting.accepted_finding_points_from_severities(["major", "blocker", "minor"], votes=["YES", "YES", "YES"]) == 2
    assert voting.accepted_finding_points_from_severities(["minor", "nit", "uncertain"]) == 1
    assert voting.accepted_finding_points_from_severities(["minor", "blocker"], votes=["YES", "NO"]) == 1
    assert voting.accepted_finding_points_from_severities(["major", "blocker", "major"], votes=["YES", "YES", "NO"]) == 2
    assert voting.accepted_finding_points_from_severities(["major", "invalid"], votes=["YES", "YES"]) == 1
    assert voting.accepted_finding_points_from_severities(["major"], votes=["YES"]) == 2
    assert voting.accepted_finding_points_from_severities(
        ["major", "major", "minor"], votes=["YES", "YES", "JUDGE_ERROR"]
    ) == 2
    labels = ["Cursor-Pragmatic", "Codex-Arch"]
    assert voting.tokenize_finding_reviewers(cell="Cursor-Pragmatic Codex-Arch", labels=labels) == labels
    assert voting.split_classification_attribution("Cursor-Pragmatic, Codex-Arch", column="finding_reviewers", labels=labels) == labels
    assert voting.raw_sole_finder_attribution(
        "Cursor-Pragmatic Codex-Arch",
        column="finding_reviewers",
        corpus_labels=labels,
    ) == labels
    assert voting.raw_sole_finder_attribution(
        "Cursor-Pragmatic Codex-Arch",
        column="finding_reviewers",
        corpus_labels=["Cursor-Pragmatic"],
    ) == []
    assert voting.raw_sole_finder_attribution(
        "Structure, Unknown",
        column="finding_reviewers",
        corpus_labels=["Structure"],
    ) == []
    assert voting.raw_sole_finder_attribution(
        "Unknown-Label",
        column="finding_reviewers",
        corpus_labels=[],
    ) == ["Unknown-Label"]
    assert voting.split_classification_attribution("cursor-a|codex-b", column="reviewer_slots") == ["cursor-a", "codex-b"]


@pytest.mark.parametrize("severity", ["major", "blocker"])
def test_neutral_high_severity_rescue_to_oos_accepts_high_yes(severity: str) -> None:
    assert voting.neutral_high_severity_rescue_to_oos(
        "neutral",
        yes_votes=[ReviewVote.yes.value, ReviewVote.no.value, ReviewVote.no.value],
        severities=[severity, "major", "major"],
    )


@pytest.mark.parametrize("severity", ["minor", "nit", "uncertain", "", "critical"])
def test_neutral_high_severity_rescue_to_oos_rejects_low_or_invalid_yes(severity: str) -> None:
    assert not voting.neutral_high_severity_rescue_to_oos(
        "neutral",
        yes_votes=[ReviewVote.yes.value, ReviewVote.no.value, ReviewVote.no.value],
        severities=[severity, "major", "major"],
    )


@pytest.mark.parametrize("result", ["accepted", "rejected"])
def test_neutral_high_severity_rescue_to_oos_requires_neutral_result(result: str) -> None:
    assert not voting.neutral_high_severity_rescue_to_oos(
        result,
        yes_votes=[ReviewVote.yes.value, ReviewVote.no.value, ReviewVote.no.value],
        severities=["major", "major", "major"],
    )


def test_neutral_high_severity_rescue_to_oos_ignores_high_no_votes() -> None:
    assert not voting.neutral_high_severity_rescue_to_oos(
        "neutral",
        yes_votes=[ReviewVote.no.value, ReviewVote.no.value, ReviewVote.no.value],
        severities=["major", "major", "major"],
    )


def test_unique_finder_bonus_from_env() -> None:
    assert voting.unique_finder_bonus_from_env({}) == 0.0
    assert voting.unique_finder_bonus_from_env({"LARCH_UNIQUE_FINDER_BONUS": ""}) == 0.0
    assert voting.unique_finder_bonus_from_env({"LARCH_UNIQUE_FINDER_BONUS": "0"}) == 0.0
    assert voting.unique_finder_bonus_from_env({"LARCH_UNIQUE_FINDER_BONUS": "-0.25"}) == 0.0
    assert voting.unique_finder_bonus_from_env({"LARCH_UNIQUE_FINDER_BONUS": "not-a-number"}) == 0.0
    assert voting.unique_finder_bonus_from_env({"LARCH_UNIQUE_FINDER_BONUS": "0.25"}) == 0.25


def test_grow_attribution_labels_skips_whitespace_combined_cells() -> None:
    labels = ["Cursor-Pragmatic", "Codex-Arch"]
    seen = set(labels)
    voting.grow_attribution_labels(labels, seen, "Cursor-Pragmatic Codex-Arch")
    assert labels == ["Cursor-Pragmatic", "Codex-Arch"]
    assert "Cursor-Pragmatic Codex-Arch" not in seen


def test_scoreboard_main_weights_classification_tsv(tmp_path: Path) -> None:
    header = voting.findings_classification_header().split("\t")

    def row(
        finding_id: str,
        reviewers: str,
        result: str,
        v1_vote: str,
        v1_severity: str,
        body: str,
        scope: str,
        *,
        v2_vote: str = "",
        v2_severity: str = "",
    ) -> str:
        cols = dict.fromkeys(header, "")
        cols.update({
            "finding_id": finding_id,
            "finding_reviewers": reviewers,
            "voting_result": result,
            "v1_vote": v1_vote,
            "v1_severity": v1_severity,
            "v2_vote": v2_vote,
            "v2_severity": v2_severity,
            "body_severity": body,
            "scope": scope,
        })
        return "\t".join(cols[name] for name in header)

    tsv = tmp_path / "classification.tsv"
    tsv.write_text(
        "\t".join(header) + "\n"
        + row("FINDING_1", "Structure", "accepted", "YES", "major", "", "in_scope", v2_vote="YES", v2_severity="blocker") + "\n"
        + row("FINDING_2", "Testing", "accepted", "YES", "minor", "important", "in_scope") + "\n"
        + row("FINDING_3", "Testing", "rejected", "NO", "major", "", "in_scope") + "\n"
        + row("FINDING_4", "Neutralist", "neutral", "YES", "minor", "", "in_scope") + "\n"
        + row("OOS_1", "Structure", "accepted", "YES", "blocker", "", "oos") + "\n"
        + row("OOS_2", "OosNeutral", "neutral", "YES", "blocker", "", "oos") + "\n",
        encoding="utf-8",
    )
    score_file = tmp_path / "score.md"
    result = run_cli(
        "voting",
        "scoreboard",
        "--findings-classification-file",
        str(tsv),
        "--reviewer-labels",
        "Structure, Testing, Neutralist, OosNeutral",
        "--output-file",
        str(score_file),
    )
    assert result.returncode == 0
    text = score_file.read_text(encoding="utf-8")
    assert "| Structure | 3 |" in text
    assert "| Testing | 0 |" in text
    assert "| Neutralist | -0.25 |" in text
    assert "| OosNeutral | 0 |" in text

    legacy_header = [name for name in header if name != "scope"]
    legacy = tmp_path / "legacy.tsv"
    legacy.write_text(
        "\t".join(legacy_header) + "\n"
        + "\t".join({**dict.fromkeys(legacy_header, ""), "finding_id": "FINDING_1", "finding_reviewers": "Structure", "voting_result": "accepted", "v1_vote": "YES", "v1_severity": "major"}[name] for name in legacy_header)
        + "\n"
        + "\t".join({**dict.fromkeys(legacy_header, ""), "finding_id": "OOS_1", "finding_reviewers": "Structure", "voting_result": "neutral", "v1_vote": "YES", "v1_severity": "major"}[name] for name in legacy_header)
        + "\n",
        encoding="utf-8",
    )
    result = run_cli(
        "voting",
        "scoreboard",
        "--findings-classification-file",
        str(legacy),
        "--reviewer-labels",
        "Structure",
        "--output-file",
        str(score_file),
    )
    assert result.returncode == 0
    assert "| Structure | 1 |" in score_file.read_text(encoding="utf-8")

    bonus_tsv = tmp_path / "bonus-classification.tsv"
    bonus_tsv.write_text(
        "\t".join(header) + "\n"
        + row("FINDING_SOLE", "Solo", "accepted", "YES", "minor", "", "in_scope") + "\n"
        + row("OOS_1", "OosOnly", "accepted", "YES", "blocker", "", "oos") + "\n"
        + row("FINDING_REJECTED", "Rejected", "rejected", "NO", "major", "", "in_scope") + "\n"
        + row("FINDING_NEUTRAL", "Neutralist", "neutral", "YES", "minor", "", "in_scope") + "\n"
        + row("FINDING_COMMA", "Structure, Testing", "accepted", "YES", "minor", "", "in_scope") + "\n"
        + row("FINDING_FILTERED_COMMA", "Structure, Unknown", "accepted", "YES", "minor", "", "in_scope") + "\n"
        + row("FINDING_WHITESPACE", "Cursor-Pragmatic Codex-Arch", "accepted", "YES", "minor", "", "in_scope") + "\n",
        encoding="utf-8",
    )
    result = run_cli(
        "voting",
        "scoreboard",
        "--findings-classification-file",
        str(bonus_tsv),
        "--reviewer-labels",
        "Solo, OosOnly, Rejected, Neutralist, Structure, Testing, Cursor-Pragmatic, Codex-Arch",
        "--output-file",
        str(score_file),
        env={**os.environ, "LARCH_UNIQUE_FINDER_BONUS": "0.25"},
    )
    assert result.returncode == 0
    text = score_file.read_text(encoding="utf-8")
    assert "| Solo | 1.25 |" in text
    assert "| OosOnly | 1 |" in text
    assert "| Rejected | -1 |" in text
    assert "| Neutralist | -0.25 |" in text
    assert "| Structure | 2 |" in text
    assert "| Testing | 1 |" in text
    assert "| Cursor-Pragmatic | 1 |" in text
    assert "| Codex-Arch | 1 |" in text


_ATTRIBUTED_BALLOT = """### FINDING_1: Codex path issue
- **Reviewer**: Codex-Structure
- **Concern**: Codex, Cursor, and Claude tools disagree on severity.
- **Suggested revision**: Fix it.

### OOS_1: [OUT_OF_SCOPE] Drift
- **Reviewer(s)**: cursor-testing-output.txt
- **Concern**: The Reviewer field name appears here in prose only.
- **Suggested revision**: File follow-up.

- Plain line mentioning Reviewer without structured label form.
"""


def test_neutralize_reviewer_attribution_preserves_body_and_labels() -> None:
    neutral = voting.neutralize_reviewer_attribution(text=_ATTRIBUTED_BALLOT)
    assert "- **Reviewer**: anonymous" in neutral
    assert "- **Reviewer(s)**: anonymous" in neutral
    assert "Codex, Cursor, and Claude" in neutral
    assert "The Reviewer field name appears here" in neutral
    assert "Plain line mentioning Reviewer" in neutral
    assert "Codex-Structure" not in neutral
    assert "cursor-testing-output.txt" not in neutral


def test_neutralize_reviewer_attribution_preserves_quoted_reviewer_in_body() -> None:
    ballot = """### FINDING_1: Example ballot line in body
- **Reviewer**: Codex-Structure
- **Concern**: Bodies may quote ballot examples.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Neutralize only the first reviewer attribution line inside each `FINDING_N` / `OOS_N` block, or use the proposer-map extraction to identify the exact attribution line to rewrite.
"""
    neutral = voting.neutralize_reviewer_attribution(text=ballot)
    assert neutral.count("anonymous") == 1
    assert "- **Reviewer**: anonymous" in neutral
    assert "From codex-generic-output.txt:" in neutral
    assert "Neutralize only the first reviewer attribution line" in neutral


def test_proposer_map_from_ballot_finding_and_oos() -> None:
    proposer_map = voting.proposer_map_from_ballot(_ATTRIBUTED_BALLOT)
    assert set(proposer_map) == {"FINDING_1", "OOS_1"}
    assert proposer_map["FINDING_1"][0] == "Codex-Structure"
    assert proposer_map["OOS_1"][0] == "cursor-testing-output.txt"


def test_validate_proposer_map_coverage_raises_on_missing() -> None:
    proposer_map = voting.proposer_map_from_ballot(_ATTRIBUTED_BALLOT)
    del proposer_map["OOS_1"]
    with pytest.raises(ValueError, match="missing item"):
        voting.validate_proposer_map_coverage(ballot_text=_ATTRIBUTED_BALLOT, proposer_map=proposer_map)


def test_restore_reviewer_attribution_replaces_anonymous_line() -> None:
    neutral_block = voting.neutralize_reviewer_attribution(
        text="### FINDING_1: Codex path issue\n- **Reviewer**: anonymous\n- **Concern**: c\n"
    )
    _, reviewer_line = voting.proposer_map_from_ballot(_ATTRIBUTED_BALLOT)["FINDING_1"]
    restored = voting.restore_reviewer_attribution(block_text=neutral_block, reviewer_line=reviewer_line)
    assert "- **Reviewer**: Codex-Structure" in restored


def test_proposer_for_item_fail_closed_without_map_entry(tmp_path: Path) -> None:
    block = tmp_path / "FINDING_1.md"
    _ = block.write_text(
        "### FINDING_1: x\n- **Reviewer**: anonymous\n- **Concern**: c\n",
        encoding="utf-8",
    )
    map_file = tmp_path / "proposer-map.tsv"
    _ = map_file.write_text("item_id\treviewer\treviewer_line\n", encoding="utf-8")
    with pytest.raises(voting.TallyError, match="missing proposer map"):
        voting.proposer_for_item(item_id="FINDING_1", block_file=block, map_file=map_file, sidecar_required=True)


def test_proposer_for_item_fallback_without_sidecar(tmp_path: Path) -> None:
    block = tmp_path / "FINDING_1.md"
    _ = block.write_text(
        "### FINDING_1: x\n- **Reviewer**: Codex-Structure\n",
        encoding="utf-8",
    )
    assert voting.proposer_for_item(item_id="FINDING_1", block_file=block, map_file="", sidecar_required=False) == "Codex-Structure"


def test_proposer_for_item_uses_sidecar_for_neutralized_block(tmp_path: Path) -> None:
    attributed = tmp_path / "attributed.md"
    _ = attributed.write_text(_ATTRIBUTED_BALLOT, encoding="utf-8")
    map_file = tmp_path / "proposer-map.tsv"
    voting.write_proposer_map(ballot_file=attributed, map_file=map_file)
    neutral_block = tmp_path / "FINDING_1.md"
    _ = neutral_block.write_text(
        voting.neutralize_reviewer_attribution(
            text="### FINDING_1: Codex path issue\n- **Reviewer**: anonymous\n- **Concern**: c\n"
        ),
        encoding="utf-8",
    )
    assert voting.proposer_for_item(item_id="FINDING_1", block_file=neutral_block, map_file=map_file, sidecar_required=True) == "Codex-Structure"


def test_proposer_for_item_ignores_stale_sidecar_for_attributed_block(tmp_path: Path) -> None:
    stale_attributed = """### FINDING_1: Old round
- **Reviewer**: Codex-Structure
- **Concern**: stale.
"""
    current_attributed = tmp_path / "current.md"
    _ = current_attributed.write_text(
        "### FINDING_1: Current round\n- **Reviewer**: Cursor-Testing\n- **Concern**: current.\n",
        encoding="utf-8",
    )
    stale_ballot = tmp_path / "stale.md"
    _ = stale_ballot.write_text(stale_attributed, encoding="utf-8")
    map_file = tmp_path / "proposer-map.tsv"
    voting.write_proposer_map(ballot_file=stale_ballot, map_file=map_file)
    current_block = tmp_path / "FINDING_1.md"
    _ = current_block.write_text(
        "### FINDING_1: Current round\n- **Reviewer**: Cursor-Testing\n- **Concern**: current.\n",
        encoding="utf-8",
    )
    assert voting.proposer_for_item(item_id="FINDING_1", block_file=current_block, map_file=map_file, sidecar_required=False) == "Cursor-Testing"


def test_write_proposer_map_roundtrip(tmp_path: Path) -> None:
    ballot = tmp_path / "ballot.md"
    _ = ballot.write_text(_ATTRIBUTED_BALLOT, encoding="utf-8")
    map_file = tmp_path / "proposer-map.tsv"
    voting.write_proposer_map(ballot_file=ballot, map_file=map_file)
    rows = voting.read_proposer_map(map_file)
    assert rows["FINDING_1"][0] == "Codex-Structure"
    assert rows["OOS_1"][0] == "cursor-testing-output.txt"
    text = map_file.read_text(encoding="utf-8")
    assert voting.PROPOSER_MAP_NEUTRAL_HASH_PREFIX in text


def test_proposer_map_from_ballot_rejects_anonymous() -> None:
    ballot = """### FINDING_1: x
- **Reviewer**: anonymous
- **Concern**: c
"""
    with pytest.raises(ValueError, match="neutral reviewer"):
        voting.proposer_map_from_ballot(ballot)


def test_write_proposer_map_rejects_neutralized_ballot(tmp_path: Path) -> None:
    ballot = tmp_path / "ballot.md"
    _ = ballot.write_text(
        voting.neutralize_reviewer_attribution(text=_ATTRIBUTED_BALLOT),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="neutralized ballot"):
        voting.write_proposer_map(ballot_file=ballot, map_file=tmp_path / "proposer-map.tsv")


def test_proposer_for_item_rejects_anonymous_sidecar_row(tmp_path: Path) -> None:
    block = tmp_path / "FINDING_1.md"
    _ = block.write_text(
        "### FINDING_1: x\n- **Reviewer**: anonymous\n- **Concern**: c\n",
        encoding="utf-8",
    )
    map_file = tmp_path / "proposer-map.tsv"
    _ = map_file.write_text(
        "item_id\treviewer\treviewer_line\n"
        "FINDING_1\tanonymous\t- **Reviewer**: anonymous\n",
        encoding="utf-8",
    )
    with pytest.raises(voting.TallyError, match="missing proposer map"):
        voting.proposer_for_item(item_id="FINDING_1", block_file=block, map_file=map_file, sidecar_required=True)


def test_validate_proposer_map_for_neutralized_ballot_rejects_stale_hash(tmp_path: Path) -> None:
    attributed = """### FINDING_1: Old round
- **Reviewer**: Codex-Structure
- **Concern**: stale.
"""
    current_attributed = """### FINDING_1: Current round
- **Reviewer**: Cursor-Testing
- **Concern**: current.
"""
    stale_ballot = tmp_path / "stale.md"
    _ = stale_ballot.write_text(attributed, encoding="utf-8")
    map_file = tmp_path / "proposer-map.tsv"
    voting.write_proposer_map(ballot_file=stale_ballot, map_file=map_file)
    neutral_ballot = tmp_path / "neutral.md"
    _ = neutral_ballot.write_text(voting.neutralize_reviewer_attribution(text=current_attributed), encoding="utf-8")
    with pytest.raises(voting.TallyError, match="stale for current ballot"):
        voting.validate_proposer_map_for_neutralized_ballot(ballot_file=neutral_ballot, map_file=map_file)


def test_voter_launcher_tool_normalizes_cursor_archetypes() -> None:
    # launch_voter_retry was removed with the parse-rate retry subsystem (main
    # #4547); the surviving contract is that cursor-* archetype voter labels
    # normalize to the "cursor" launcher tool, while non-archetype labels pass
    # through unchanged.
    assert voting.voter_launcher_tool("cursor-validity") == "cursor"
    assert voting.voter_launcher_tool("cursor-plan-fidelity") == "cursor"
    assert voting.voter_launcher_tool("cursor-pragmatism") == "cursor"
    assert voting.voter_launcher_tool("claude") == "claude"
    assert voting.voter_launcher_tool("codex") == "codex"
    assert voting.voter_launcher_tool("cursor") == "cursor"


def test_judge_severity_enum_is_shared_and_public_boundaries_return_strings() -> None:
    assert voting.JudgeSeverity is JudgeSeverity
    assert voting.SEVERITY_BLOCKER == "blocker"
    assert voting.SEVERITY_MAJOR == "major"
    assert voting.valid_panel_severity("nit") == "nit"
    assert voting.valid_panel_severity("uncertain") == "uncertain"
    assert voting.valid_panel_severity("critical") is None


def test_parse_judge_vote_keeps_string_return_types_for_enum_values(tmp_path: Path) -> None:
    voter = tmp_path / "voter.txt"
    voter.write_text("FINDING_1: YES CORRECTNESS=true SEVERITY=uncertain QUALITY=good UNCERTAIN=false\n", encoding="utf-8")

    vote, _correctness, severity, _quality, _uncertain = voting.parse_judge_vote(voter_file=voter, ballot_id="FINDING_1")

    assert vote == "YES"
    assert not isinstance(vote, ReviewVote)
    assert severity == "uncertain"
    assert not isinstance(severity, JudgeSeverity)


def test_voter_calibration_base_tool_normalization_and_snapshot_round_trip(tmp_path: Path) -> None:
    assert voting.normalize_voter_label_to_base_tool("Codex-plan-fidelity") == "codex"
    assert voting.normalize_voter_label_to_base_tool("cursor-validity") == "cursor"
    assert voting.normalize_voter_label_to_base_tool("Claude") == "claude"
    assert voting.normalize_voter_label_to_base_tool("v1") == "cursor"
    assert voting.normalize_voter_label_to_base_tool("v2") == "codex"
    assert voting.normalize_voter_label_to_base_tool("unknown") is None

    path = tmp_path / "stats.tsv"
    stat = voting.VoterCalibrationStat(
        tool="codex",
        yes_votes=3,
        valid_yes_severity_count=2,
        blocker=1,
        major=1,
        minor=0,
        nit=0,
        uncertain=0,
        missing_severity=1,
        high_rate=1.0,
        calibration_score=0.0,
        uncalibrated=True,
    )
    assert voting.write_voter_calibration_stats(path=path, stats=[stat])
    loaded = voting.read_voter_calibration_stats(path)
    assert loaded["codex"] == stat


def test_voter_calibration_log_window_groups_by_run_dir(tmp_path: Path) -> None:
    root = tmp_path / "larch-logs"
    newer = root / "implement" / "newer"
    older = root / "implement" / "older"
    for run, started, severity in ((newer, "2026-01-02T00:00:00Z", "major"), (older, "2026-01-01T00:00:00Z", "minor")):
        round_dir = run / "round-1"
        round_dir.mkdir(parents=True)
        (run / "manifest.json").write_text(json.dumps({"started_at": started}), encoding="utf-8")
        (round_dir / "findings-classification.tsv").write_text(
            voting.CODE_REVIEW_FINDINGS_CLASSIFICATION_HEADER
            + f"\nFINDING_1\treviewer\taccepted\tYES\ttrue\t{severity}\tgood\tfalse\tcodex\tNO\ttrue\tminor\tgood\tfalse\tcursor\tYES\ttrue\tminor\tgood\tfalse\tclaude\tin\n",
            encoding="utf-8",
        )
    stats = voting.voter_calibration_stats_from_logs(log_root=root, window=1)
    codex = next(stat for stat in stats if stat.tool == "codex")
    assert codex.major == 1
    assert codex.minor == 0


def test_resolve_voter_calibration_log_root_design_source_env_repo_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    consumer = tmp_path / "consumer"
    (consumer / "larch-logs").mkdir(parents=True)
    design = tmp_path / "design"
    design.mkdir()
    (design / "source-env.sh").write_text(f"REPO_ROOT={consumer}\n", encoding="utf-8")
    monkeypatch.delenv("LARCH_CONSUMER_REPO", raising=False)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    root = voting._resolve_voter_calibration_log_root(design_tmpdir=design, review_tmpdir=None)  # pyright: ignore[reportPrivateUsage]
    assert root == (consumer / "larch-logs").resolve()


def test_resolve_voter_calibration_log_root_design_env_repo_root_precedence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_repo = tmp_path / "env-repo"
    (env_repo / "larch-logs").mkdir(parents=True)
    design = tmp_path / "design"
    design.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    (design / "source-env.sh").write_text(f"REPO_ROOT={other}\n", encoding="utf-8")
    monkeypatch.delenv("LARCH_CONSUMER_REPO", raising=False)
    monkeypatch.setenv("REPO_ROOT", str(env_repo))
    root = voting._resolve_voter_calibration_log_root(design_tmpdir=design, review_tmpdir=None)  # pyright: ignore[reportPrivateUsage]
    assert root == (env_repo / "larch-logs").resolve()


def test_resolve_voter_calibration_log_root_implement_session_env_repo_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    consumer = tmp_path / "consumer"
    (consumer / "larch-logs").mkdir(parents=True)
    implement = tmp_path / "implement"
    implement.mkdir()
    review = implement / "round-1"
    review.mkdir()
    (implement / "session-env.sh").write_text(f"REPO_CWD={consumer}\n", encoding="utf-8")
    monkeypatch.delenv("LARCH_CONSUMER_REPO", raising=False)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    root = voting._resolve_voter_calibration_log_root(design_tmpdir=None, review_tmpdir=review)  # pyright: ignore[reportPrivateUsage]
    assert root == (consumer / "larch-logs").resolve()


def test_resolve_voter_calibration_log_root_prefers_implement_over_review_keepalive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    implement_repo = tmp_path / "implement-repo"
    (implement_repo / "larch-logs").mkdir(parents=True)
    review_repo = tmp_path / "review-repo"
    (review_repo / "larch-logs").mkdir(parents=True)
    implement = tmp_path / "implement"
    implement.mkdir()
    review = implement / "round-1"
    review.mkdir()
    (implement / "session-env.sh").write_text(f"REPO_CWD={implement_repo}\n", encoding="utf-8")
    (review / ".larch-keepalive").write_text(f"CLONE_PATH={review_repo}\n", encoding="utf-8")
    monkeypatch.delenv("LARCH_CONSUMER_REPO", raising=False)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    root = voting._resolve_voter_calibration_log_root(design_tmpdir=None, review_tmpdir=review)  # pyright: ignore[reportPrivateUsage]
    assert root == (implement_repo / "larch-logs").resolve()


def test_resolve_voter_calibration_log_root_review_keepalive_when_session_stale(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    consumer = tmp_path / "consumer"
    (consumer / "larch-logs").mkdir(parents=True)
    plugin = tmp_path / "plugin"
    (plugin / "larch-logs").mkdir(parents=True)
    implement = tmp_path / "implement"
    implement.mkdir()
    review = implement / "round-1"
    review.mkdir()
    (implement / "session-env.sh").write_text("# stale session without repo anchors\n", encoding="utf-8")
    (review / ".larch-keepalive").write_text(f"CLONE_PATH={consumer}\n", encoding="utf-8")
    monkeypatch.delenv("LARCH_CONSUMER_REPO", raising=False)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.chdir(plugin)
    root = voting._resolve_voter_calibration_log_root(design_tmpdir=None, review_tmpdir=review)  # pyright: ignore[reportPrivateUsage]
    assert root == (consumer / "larch-logs").resolve()


def test_resolve_voter_calibration_log_root_design_rejects_plugin_cwd_without_anchor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    (plugin / "larch-logs").mkdir()
    design = tmp_path / "design"
    design.mkdir()
    (design / "source-env.sh").write_text("# no REPO_ROOT\n", encoding="utf-8")
    monkeypatch.delenv("LARCH_CONSUMER_REPO", raising=False)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plugin))
    monkeypatch.chdir(plugin)
    with pytest.raises(ValueError, match="design calibration log root unresolved"):
        voting._resolve_voter_calibration_log_root(design_tmpdir=design, review_tmpdir=None)  # pyright: ignore[reportPrivateUsage]


def test_resolve_voter_calibration_log_root_design_rejects_plugin_root_without_claude_plugin_root_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / "source-env.sh").write_text("# no REPO_ROOT\n", encoding="utf-8")
    monkeypatch.delenv("LARCH_CONSUMER_REPO", raising=False)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.delenv("REPO_ROOT", raising=False)
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    monkeypatch.chdir(voting._plugin_root())  # pyright: ignore[reportPrivateUsage]
    with pytest.raises(ValueError, match="design calibration log root unresolved"):
        voting._resolve_voter_calibration_log_root(design_tmpdir=design, review_tmpdir=None)  # pyright: ignore[reportPrivateUsage]


def test_resolve_voter_calibration_log_root_review_fails_closed_without_anchors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    implement = tmp_path / "implement"
    implement.mkdir()
    review = implement / "round-1"
    review.mkdir()
    (implement / "session-env.sh").write_text("# no anchors\n", encoding="utf-8")
    monkeypatch.delenv("LARCH_CONSUMER_REPO", raising=False)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    monkeypatch.chdir(voting._plugin_root())  # pyright: ignore[reportPrivateUsage]
    with pytest.raises(ValueError, match="review calibration log root unresolved"):
        voting._resolve_voter_calibration_log_root(design_tmpdir=None, review_tmpdir=review)  # pyright: ignore[reportPrivateUsage]


def test_resolve_voter_calibration_log_root_prefers_larch_consumer_repo_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    consumer = tmp_path / "consumer"
    (consumer / "larch-logs").mkdir(parents=True)
    monkeypatch.setenv("LARCH_CONSUMER_REPO", str(consumer))
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    root = voting._resolve_voter_calibration_log_root(design_tmpdir=None, review_tmpdir=None)  # pyright: ignore[reportPrivateUsage]
    assert root == (consumer / "larch-logs").resolve()


def test_voter_calibration_snapshot_main_reads_env_window(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_root = tmp_path / "larch-logs"
    run = log_root / "implement" / "run-a"
    round_dir = run / "round-1"
    round_dir.mkdir(parents=True)
    (run / "manifest.json").write_text('{"started_at": "2026-01-02T00:00:00Z"}\n', encoding="utf-8")
    (round_dir / "findings-classification.tsv").write_text(
        voting.CODE_REVIEW_FINDINGS_CLASSIFICATION_HEADER
        + "\nFINDING_1\treviewer\taccepted\tYES\ttrue\tmajor\tgood\tfalse\tcodex\tNO\ttrue\tminor\tgood\tfalse\tcursor\tYES\ttrue\tminor\tgood\tfalse\tclaude\tin\n",
        encoding="utf-8",
    )
    out = tmp_path / "stats.tsv"
    monkeypatch.delenv(config.ENV_LARCH_VOTER_CALIBRATION_WINDOW, raising=False)
    rc = voting.voter_calibration_snapshot_main(["--log-root", str(log_root), "--out", str(out)])
    assert rc == 0
    assert out.is_file()
    monkeypatch.setenv(config.ENV_LARCH_VOTER_CALIBRATION_WINDOW, "1")
    out2 = tmp_path / "stats-window.tsv"
    rc = voting.voter_calibration_snapshot_main(["--log-root", str(log_root), "--out", str(out2)])
    assert rc == 0
    assert out2.is_file()


def test_voter_calibration_snapshot_main_malformed_env_window_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_root = tmp_path / "larch-logs"
    log_root.mkdir()
    out = tmp_path / "stats.tsv"
    monkeypatch.setenv(config.ENV_LARCH_VOTER_CALIBRATION_WINDOW, "not-a-number")
    rc = voting.voter_calibration_snapshot_main(["--log-root", str(log_root), "--out", str(out)])
    assert rc == 0
    assert voting._resolve_voter_calibration_window("not-a-number") == config.VOTER_CALIBRATION_WINDOW_DEFAULT  # pyright: ignore[reportPrivateUsage]


def test_voter_calibration_design_multi_round_grouping(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs"
    run = log_root / "design" / "session-a"
    for round_num in (1, 2):
        round_dir = run / "plan-review" / f"round-{round_num}"
        round_dir.mkdir(parents=True)
        (round_dir / "findings-classification.tsv").write_text(
            voting.CODE_REVIEW_FINDINGS_CLASSIFICATION_HEADER
            + "\nFINDING_1\treviewer\taccepted\tYES\ttrue\tmajor\tgood\tfalse\tcodex\tNO\ttrue\tminor\tgood\tfalse\tcursor\tYES\ttrue\tminor\tgood\tfalse\tclaude\tin\n",
            encoding="utf-8",
        )
    (run / "manifest.json").write_text('{"started_at": "2026-01-02T00:00:00Z"}\n', encoding="utf-8")
    rows = voting.discover_voter_calibration_logs(log_root)
    assert len({row.run_dir for row in rows}) == 1


def test_voter_calibration_flat_review_run_dir_grouping(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs"
    run = log_root / "review" / "run-flat"
    run.mkdir(parents=True)
    (run / "review-findings-classification-round-1.tsv").write_text(
        voting.CODE_REVIEW_FINDINGS_CLASSIFICATION_HEADER
        + "\nFINDING_1\treviewer\taccepted\tYES\ttrue\tmajor\tgood\tfalse\tcodex\tNO\ttrue\tminor\tgood\tfalse\tcursor\tYES\ttrue\tminor\tgood\tfalse\tclaude\tin\n",
        encoding="utf-8",
    )
    rows = voting.discover_voter_calibration_logs(log_root)
    assert rows[0].run_dir == run


def test_voter_calibration_snapshot_skips_unsupported_tsv(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs"
    run = log_root / "implement" / "run-bad"
    round_dir = run / "round-1"
    round_dir.mkdir(parents=True)
    (run / "manifest.json").write_text('{"started_at": "2026-01-02T00:00:00Z"}\n', encoding="utf-8")
    (round_dir / "findings-classification.tsv").write_text("not-a-tsv-header\n", encoding="utf-8")
    stats = voting.voter_calibration_stats_from_logs(log_root=log_root, window=1)
    assert stats == []


def test_voter_calibration_snapshot_zero_severity_yes_votes_omitted(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs"
    run = log_root / "implement" / "run-zero"
    round_dir = run / "round-1"
    round_dir.mkdir(parents=True)
    (run / "manifest.json").write_text('{"started_at": "2026-01-02T00:00:00Z"}\n', encoding="utf-8")
    (round_dir / "findings-classification.tsv").write_text(
        voting.CODE_REVIEW_FINDINGS_CLASSIFICATION_HEADER
        + "\nFINDING_1\treviewer\taccepted\tNO\ttrue\t\t\t\t\tcodex\tNO\ttrue\t\t\t\tcursor\tNO\ttrue\t\t\t\tclaude\tin\n",
        encoding="utf-8",
    )
    stats = voting.voter_calibration_stats_from_logs(log_root=log_root, window=1)
    assert stats == []
