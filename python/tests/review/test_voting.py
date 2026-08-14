# pyright: reportMissingParameterType=false, reportUnknownParameterType=false
from __future__ import annotations

# pyright: reportUnusedCallResult=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportArgumentType=false

import json
import subprocess
import sys
from pathlib import Path
from typing import cast

import pytest

from larch.review import voting
from larch.core import config
from larch.review.review_types import (
    JudgeSeverity,
    ReviewVote,
    code_review_classification_header,
    code_review_classification_required_fields,
)
from tests.support.review_wire import vote_lines
from tests.support.foundation import make_keepalive_consumer_fixture

CLI = Path(__file__).resolve().parents[2] / "cli.py"


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
        vote_lines({"FINDING_1": "YES", "FINDING_10": "YES"}) + "finding_1: exonerate -- old token\n",
        encoding="utf-8",
    )
    assert voting.vote_for_id(ballot_id="FINDING_1", voter_file=voter) == "NO"


def test_vote_for_id_text_uses_the_file_vote_grammar() -> None:
    assert voting.vote_for_id_text(
        ballot_id="FINDING_1",
        text="FINDING_1: YES\nFINDING_1: EXONERATE\n",
    ) == "NO"


def test_reviewer_security_and_split_ballot(tmp_path: Path) -> None:
    ballot = tmp_path / "ballot.md"
    ballot.write_text(
        "intro\n"
        "### FINDING_1: one\n- **Reviewer**: Structure\n- **Focus-Area**: security\n"
        "### OOS_2: two\nbody\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "blocks"
    voting.split_ballot(ballot_file=ballot, out_dir=out_dir)
    assert (out_dir / "FINDING_1.md").exists()
    assert voting.reviewer_for_block(out_dir / "FINDING_1.md") == "Structure"
    assert voting.is_security_block(out_dir / "FINDING_1.md")

def test_ballot_blocks_use_canonical_parser_and_exact_item_slices(tmp_path: Path) -> None:
    ballot_text = (
        "Preamble stays outside ballot blocks.\n"
        "```markdown\n"
        "### FINDING_99: fenced heading\n"
        "```\n"
        "###   FINDING_1: spaced heading\n"
        "- **Reviewer**: Codex-Structure\n"
        "body one\n"
        "###\tOOS_2:\ttab heading\n"
        "- **Reviewer**: Cursor-Testing\n"
        "body two\n"
    )
    expected = {
        "FINDING_1": "###   FINDING_1: spaced heading\n- **Reviewer**: Codex-Structure\nbody one\n",
        "OOS_2": "###\tOOS_2:\ttab heading\n- **Reviewer**: Cursor-Testing\nbody two\n",
    }

    assert voting.proposer_map_from_ballot(ballot_text) == {
        "FINDING_1": ("Codex-Structure", "- **Reviewer**: Codex-Structure"),
        "OOS_2": ("Cursor-Testing", "- **Reviewer**: Cursor-Testing"),
    }

    ballot = tmp_path / "ballot.md"
    ballot.write_text(ballot_text, encoding="utf-8")
    out_dir = tmp_path / "blocks"
    voting.split_ballot(ballot_file=ballot, out_dir=out_dir)
    assert (out_dir / "FINDING_1.md").read_text(encoding="utf-8") == expected["FINDING_1"]
    assert (out_dir / "OOS_2.md").read_text(encoding="utf-8") == expected["OOS_2"]


def test_ballot_parser_rejects_canonical_whitespace_duplicate_and_missing_proposer(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    duplicate = "### FINDING_1: one\n### \tFINDING_1: duplicate\n"
    ballot = tmp_path / "duplicate.md"
    ballot.write_text(duplicate, encoding="utf-8")
    with pytest.raises(SystemExit, match="1"):
        voting.split_ballot(ballot_file=ballot, out_dir=tmp_path / "blocks")
    assert capsys.readouterr().err == "duplicate ballot heading FINDING_1\n"

    missing_proposer = "### \tFINDING_1: one\n- **Concern**: missing reviewer\n"
    with pytest.raises(ValueError, match="proposer map missing item"):
        voting.validate_proposer_map_coverage(
            ballot_text=missing_proposer,
            proposer_map=voting.proposer_map_from_ballot(missing_proposer),
        )


def test_neutralization_uses_canonical_whitespace_heading() -> None:
    ballot = "### \tFINDING_1: one\n- **Reviewer**: Codex-Structure\n"
    neutral = voting.neutralize_reviewer_attribution(text=ballot)

    assert neutral == "### \tFINDING_1: one\n- **Reviewer**: anonymous\n"
    assert voting.ballot_text_is_neutralized(neutral)


@pytest.mark.parametrize(
    "text",
    [
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


def test_is_security_block_text_ignores_description_prose() -> None:
    assert not voting.is_security_block_text(
        "### OOS_1: Some finding\n"
        "- **Description**: The affected block uses focus-area=security metadata.\n"
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
    vote, correctness, _severity, _quality, uncertain = voting.parse_judge_vote(
        voter_file=voter,
        ballot_id="FINDING_1",
    )
    assert vote == expected_vote
    assert correctness == expected_correctness
    assert uncertain == expected_uncertain


def test_parse_judge_vote_unreadable_library_path(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        voting.parse_judge_vote(voter_file=tmp_path / "missing.txt", ballot_id="FINDING_1")


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


def test_alias_ballot_id_accepts_safe_finding_and_oos_aliases() -> None:
    assert voting.alias_ballot_id("FINDING_6", {"FINDING_6"}) == "OOS_6"
    assert voting.alias_ballot_id("OOS_6", {"OOS_6"}) == "FINDING_6"
    assert voting.alias_ballot_id("FINDING_1", {"FINDING_1", "OOS_1"}) == ""
    assert voting.alias_ballot_id("NOTE_1", {"NOTE_1"}) == ""


def test_vote_for_id_accepts_alias_when_primary_missing(tmp_path: Path) -> None:
    voter = tmp_path / "voter.txt"
    voter.write_text("OOS_6: YES -- relabeled out-of-scope finding\n", encoding="utf-8")

    assert voting.vote_for_id(ballot_id="FINDING_6", voter_file=voter) == "JUDGE_ERROR"
    assert voting.vote_for_id(ballot_id="FINDING_6", voter_file=voter, alias_id="OOS_6") == "YES"


def test_parse_judge_vote_accepts_alias_and_preserves_axes(tmp_path: Path) -> None:
    voter = tmp_path / "voter.txt"
    voter.write_text(
        "OOS_6: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false -- relabeled\n",
        encoding="utf-8",
    )

    vote, correctness, severity, quality, uncertain = voting.parse_judge_vote(
        voter_file=voter,
        ballot_id="FINDING_6",
        alias_id="OOS_6",
    )

    assert vote == "YES"
    assert correctness == "true"
    assert severity == "major"
    assert quality == "good"
    assert uncertain == "false"


def test_primary_vote_wins_over_alias_vote(tmp_path: Path) -> None:
    voter = tmp_path / "voter.txt"
    voter.write_text(
        "OOS_6: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n"
        "FINDING_6: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false\n",
        encoding="utf-8",
    )

    assert voting.vote_for_id(ballot_id="FINDING_6", voter_file=voter, alias_id="OOS_6") == "NO"
    vote, correctness, severity, quality, uncertain = voting.parse_judge_vote(
        voter_file=voter,
        ballot_id="FINDING_6",
        alias_id="OOS_6",
    )

    assert vote == "NO"
    assert correctness == "false-positive"
    assert severity == "nit"
    assert quality == "no-fix"
    assert uncertain == "false"


def test_anchored_votes_unaffected_by_markdown_normalization(tmp_path: Path) -> None:
    # Plain anchored votes (no pipe characters) pass through unchanged.
    voter = tmp_path / "voter.txt"
    voter.write_text("FINDING_1: YES\nFINDING_2: NO -- reason\n", encoding="utf-8")
    assert voting.vote_for_id(ballot_id="FINDING_1", voter_file=voter) == "YES"
    assert voting.vote_for_id(ballot_id="FINDING_2", voter_file=voter) == "NO"


def test_file_line_regex_library_remains_for_python_consumers() -> None:
    assert "Makefile" in voting.FILE_LINE_REGEXES["extensionless-re"]


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
    assert [label for label, _vote in prep.voter_votes] == ["codex-validity", "codex-plan-fidelity", "codex-pragmatism"]
    assert parsed["voters"][0]["voter"] == "codex-validity"  # type: ignore[reportIndexIssue]


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
            voter_severities=[severity, "major", "major"],
            panel="code-review",
        )
        for vote, severity in [
            *[("YES", "major") for _ in range(9)],
            ("YES", "minor"),
            ("YES", ""),
            ("YES", "bogus"),
            ("NO", "major"),
        ]
    ]
    eligible_rows = [row for row in rows if row is not None]
    records = voting.compute_voter_severity_distribution(eligible_rows)
    v1 = next(record for record in records if record["voter"] == "v1")
    assert v1["yes_votes"] == 12
    assert v1["major"] == 9
    assert v1["minor"] == 1
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
    assert "| undefined | n/a | 0 | 0 | 0 | 0 | 0 | n/a | n/a | false |" in rendered


def test_render_voter_severity_scoreboard_calibration_score() -> None:
    rendered = voting.render_voter_severity_scoreboard([
        {
            "panel": "code-review",
            "voter": "mixed",
            "yes_votes": 10,
            "major": 9,
            "minor": 0,
            "nit": 0,
            "missing_severity": 0,
            "high_rate": 0.9,
            "calibration_score": 1.0,
            "uncalibrated": False,
        },
        {
            "panel": "code-review",
            "voter": "all-high",
            "yes_votes": 10,
            "major": 10,
            "minor": 0,
            "nit": 0,
            "missing_severity": 0,
            "high_rate": 1.0,
            "calibration_score": 0.0,
            "uncalibrated": True,
        },
    ])
    assert "| code-review | mixed | 10 | 9 | 0 | 0 | 0 | 0.900 | 1.000 | false |" in rendered
    assert "| code-review | all-high | 10 | 10 | 0 | 0 | 0 | 1.000 | 0.000 | true |" in rendered


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


def test_code_review_classification_header_variants_share_one_schema() -> None:
    full = code_review_classification_header(include_tools=True, include_scope=True)
    compact = code_review_classification_header(include_tools=False, include_scope=False)
    tally = code_review_classification_header(include_tools=False, include_scope=True)

    assert full == voting.CODE_REVIEW_FINDINGS_CLASSIFICATION_HEADER
    assert compact + "\tscope" == tally
    assert "v1_tool" not in tally
    assert code_review_classification_required_fields(
        include_tools=True, include_scope=True
    ) == frozenset(full.split("\t"))


def test_findings_classification_header_library() -> None:
    assert voting.findings_classification_header() == voting.FINDINGS_CLASSIFICATION_HEADER


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
    assert voting.accepted_finding_points_from_severities(["major", "blocker"]) == 1
    assert voting.accepted_finding_points_from_severities(["major", "blocker"], votes=["YES", "YES"]) == 1
    assert voting.accepted_finding_points_from_severities(["major", "minor"], votes=["YES", "YES"]) == 1
    assert voting.accepted_finding_points_from_severities(["major", "minor", "minor"], votes=["YES", "YES", "YES"]) == 1
    assert voting.accepted_finding_points_from_severities(["major", "blocker", "minor"], votes=["YES", "YES", "YES"]) == 1
    assert voting.accepted_finding_points_from_severities(["minor", "nit", "uncertain"]) == 1
    assert voting.accepted_finding_points_from_severities(["minor", "blocker"], votes=["YES", "NO"]) == 1
    assert voting.accepted_finding_points_from_severities(["major", "blocker", "major"], votes=["YES", "YES", "NO"]) == 1
    assert voting.accepted_finding_points_from_severities(["major", "invalid"], votes=["YES", "YES"]) == 1
    assert voting.accepted_finding_points_from_severities(["major"], votes=["YES"]) == 2
    assert voting.accepted_finding_points_from_severities(
        ["major", "major", "minor"], votes=["YES", "YES", "JUDGE_ERROR"]
    ) == 2
    labels = ["Cursor-Pragmatic", "Codex-Arch"]
    assert voting.tokenize_finding_reviewers(cell="Cursor-Pragmatic Codex-Arch", labels=labels) == labels
    assert voting.split_classification_attribution("Cursor-Pragmatic, Codex-Arch", column="finding_reviewers", labels=labels) == labels
    assert voting.split_classification_attribution("cursor-a|codex-b", column="reviewer_slots") == ["cursor-a", "codex-b"]


@pytest.mark.parametrize("severity", ["major"])
def test_neutral_high_severity_rescue_to_oos_accepts_high_yes(severity: str) -> None:
    assert voting.neutral_high_severity_rescue_to_oos(
        "neutral",
        yes_votes=[ReviewVote.yes.value, ReviewVote.no.value, ReviewVote.no.value],
        severities=[severity, "major", "major"],
    )


@pytest.mark.parametrize("severity", ["minor", "nit", "blocker", "uncertain", "", "critical"])
def test_neutral_high_severity_rescue_to_oos_rejects_low_or_invalid_yes(severity: str) -> None:
    assert not voting.neutral_high_severity_rescue_to_oos(
        "neutral",
        yes_votes=[ReviewVote.yes.value, ReviewVote.no.value, ReviewVote.no.value],
        severities=[severity, "major", "major"],
    )


def test_oos_fileable_from_votes_requires_accepted_strict_yes_majority() -> None:
    assert voting.oos_fileable_from_votes(
        "accepted",
        yes_votes=["YES", "YES", "NO"],
        severities=["major", "major", "minor"],
    )
    assert not voting.oos_fileable_from_votes(
        "accepted",
        yes_votes=["YES", "YES", "NO"],
        severities=["major", "minor", "major"],
    )
    assert not voting.oos_fileable_from_votes(
        "neutral",
        yes_votes=["YES"],
        severities=["major"],
    )
    assert not voting.oos_fileable_from_votes(
        "accepted",
        yes_votes=["YES"],
        severities=["blocker"],
    )


def test_artifact_marked_fileable_requires_exact_true_marker() -> None:
    assert voting.artifact_marked_fileable("Vote tally: YES=1 Result=accepted Fileable=true\n")
    assert not voting.artifact_marked_fileable("Vote tally: YES=1 Result=accepted Fileable=true-extra\n")
    assert not voting.artifact_marked_fileable("Vote tally: YES=1 Result=accepted Fileable=false\n")


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


def test_judge_severity_enum_is_shared_and_public_boundaries_return_strings() -> None:
    assert voting.JudgeSeverity is JudgeSeverity
    assert voting.SEVERITY_MAJOR == "major"
    assert voting.valid_panel_severity("nit") == "nit"
    assert voting.valid_panel_severity("blocker") == "major"
    assert voting.valid_panel_severity("uncertain") is None
    assert voting.valid_panel_severity("critical") is None


def test_parse_judge_vote_keeps_string_return_types_for_enum_values(tmp_path: Path) -> None:
    voter = tmp_path / "voter.txt"
    voter.write_text("FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n", encoding="utf-8")

    vote, _correctness, severity, _quality, _uncertain = voting.parse_judge_vote(voter_file=voter, ballot_id="FINDING_1")

    assert vote == "YES"
    assert not isinstance(vote, ReviewVote)
    assert severity == "major"
    assert not isinstance(severity, JudgeSeverity)


def test_voter_calibration_base_tool_normalization_and_snapshot_round_trip(tmp_path: Path) -> None:
    assert voting.normalize_voter_label_to_base_tool("Codex-plan-fidelity") == "codex"
    assert voting.normalize_voter_label_to_base_tool("codex-validity") == "codex"
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
        major=2,
        minor=0,
        nit=0,
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
    consumer, plugin, _implement, review = make_keepalive_consumer_fixture(
        tmp_path, session_text="# stale session without repo anchors\n"
    )
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


def test_discover_voter_calibration_logs_skips_symlinks_and_keeps_order(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs"
    implement = log_root / "implement" / "run-real" / "round-2"
    implement.mkdir(parents=True)
    (implement / "findings-classification.tsv").write_text("h\n", encoding="utf-8")
    earlier = log_root / "implement" / "run-real" / "round-10"
    earlier.mkdir(parents=True)
    (earlier / "findings-classification.tsv").write_text("h\n", encoding="utf-8")
    linked = log_root / "implement" / "run-link"
    linked.symlink_to(log_root / "implement" / "run-real")
    rows = voting.discover_voter_calibration_logs(log_root)
    assert [row.path.parent.name for row in rows] == ["round-10", "round-2"]
