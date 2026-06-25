"""Tests for OOS wire-format helpers."""

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

if TYPE_CHECKING:
    import pytest

import oos


CLI_PATH = Path(__file__).with_name("cli.py")


FIXTURE_FINDINGS = """### FINDING_1: [OUT_OF_SCOPE] Public cleanup
- **Concern**: Cleanup.
### FINDING_2: [OUT_OF_SCOPE] Secret issue
- **Concern**: focus-area=security secret.
### FINDING_3: [OUT_OF_SCOPE] Rejected cleanup
- **Concern**: Do not file.
Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected
### FINDING_4: [OUT_OF_SCOPE] Result accepted cleanup
- **Concern**: File only accepted result.
Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted
### FINDING_5: [OUT_OF_SCOPE] ordinary security cleanup
- **Concern**: Public non-sensitive title.
### FINDING_6: [OUT_OF_SCOPE] `[security]` tagged title
- **Concern**: Header tag must hold.
### FINDING_7: [OUT_OF_SCOPE] Backtick value
- **focus-area**: `security-hardening`
### FINDING_8: [OUT_OF_SCOPE] Cited security heading
- **Concern**: This mentions a later example heading.
### Example [security] policy
### FINDING_9: [OUT_OF_SCOPE] Prose result token
- **Concern**: Mentions Result=rejected in prose, but has no tally footer.
"""


def _write_findings(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "findings.md"
    _ = path.write_text(text, encoding="utf-8")
    return path


def _serialize_text(tmp_path: Path, text: str) -> tuple[tuple[int, int], str]:
    findings = _write_findings(tmp_path, text)
    output = tmp_path / "out" / "oos.md"
    counts = oos.oos_serialize(findings_file=findings, output_file=output)
    return counts, output.read_text(encoding="utf-8")


def _run_cli(args: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI_PATH), *args],
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
    )


def test_normalize_header_tagged_finding() -> None:
    text = "### FINDING_3: [OUT_OF_SCOPE] Timing harness coverage\n- **Description**: body.\n"
    assert oos.normalize_oos_block_header(seq=1, block_text=text).splitlines()[0] == (
        "### OOS_1: [OUT_OF_SCOPE] Timing harness coverage"
    )


def test_normalize_header_bare_finding() -> None:
    text = "### FINDING_2: Drifted finding\n- **Concern**: drift.\n"
    assert oos.normalize_oos_block_header(seq=2, block_text=text).splitlines()[0] == "### OOS_2: Drifted finding"


def test_normalize_header_renumber() -> None:
    text = "### OOS_9: Already canonical id\n"
    assert oos.normalize_oos_block_header(seq=3, block_text=text) == "### OOS_3: Already canonical id\n"


def test_normalize_header_nr1_guard() -> None:
    text = "### FINDING_1: [OUT_OF_SCOPE] Outer\n### FINDING_2: cited heading in body\n- tail\n"
    assert oos.normalize_oos_block_header(seq=4, block_text=text) == (
        "### OOS_4: [OUT_OF_SCOPE] Outer\n### FINDING_2: cited heading in body\n- tail\n"
    )


def test_normalize_header_no_id_token() -> None:
    assert oos.normalize_oos_block_header(seq=6, block_text="prose line, not a header\n") == (
        "prose line, not a header\n"
    )


def test_normalize_header_stdin_cli_via_subprocess() -> None:
    result = _run_cli(
        ["oos", "normalize-header", "--seq", "5"],
        input_text="### FINDING_7: [OOS] Stdin block\n",
    )
    assert result.returncode == 0
    assert result.stdout == "### OOS_5: [OOS] Stdin block\n"
    assert result.stderr == ""


def test_normalize_header_cli_via_subprocess(tmp_path: Path) -> None:
    block = tmp_path / "block.md"
    fd3 = tmp_path / "fd3.out"
    _ = block.write_text("### FINDING_8: [OUT_OF_SCOPE] File block\n", encoding="utf-8")
    cmd = (
        f"{shlex.quote(sys.executable)} {shlex.quote(str(CLI_PATH))} "
        f"oos normalize-header --seq 7 --block-file {shlex.quote(str(block))} "
        f"3>{shlex.quote(str(fd3))}"
    )
    result = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert result.stdout == "### OOS_7: [OUT_OF_SCOPE] File block\n"
    assert result.stdout
    assert fd3.read_text(encoding="utf-8") == ""
    assert "OOS_7" not in result.stderr


def test_normalize_header_cli_validation_exit_2(tmp_path: Path) -> None:
    block = tmp_path / "block.md"
    _ = block.write_text("### FINDING_1: [OOS] Payload\n", encoding="utf-8")
    cases = [
        ["oos", "normalize-header", "--seq", "notanumber", "--block-file", str(block)],
        ["oos", "normalize-header", "--block-file", str(block)],
        ["oos", "normalize-header", "--seq", "1", "--block-file", str(tmp_path / "nope.md")],
    ]
    for args in cases:
        result = _run_cli(args)
        assert result.returncode == 2
        assert "Payload" not in result.stdout


def test_oos_serialize_harness_fixture_exact_counts(tmp_path: Path) -> None:
    counts, output = _serialize_text(tmp_path, FIXTURE_FINDINGS)
    assert counts == (5, 3)
    for title in [
        "Public cleanup",
        "Result accepted cleanup",
        "ordinary security cleanup",
        "Cited security heading",
        "Prose result token",
    ]:
        assert title in output
    for absent in ["Secret issue", "Rejected cleanup", "tagged title", "Backtick value"]:
        assert absent not in output
    for seq in range(1, 6):
        assert f"### OOS_{seq}:" in output


def test_oos_serialize_result_rejected_skipped(tmp_path: Path) -> None:
    counts, output = _serialize_text(
        tmp_path,
        """### FINDING_1: [OUT_OF_SCOPE] Rejected
Vote tally: YES=0 NO=3 Result=rejected
""",
    )
    assert counts == (0, 0)
    assert output == ""


def test_oos_serialize_result_neutral_skipped(tmp_path: Path) -> None:
    counts, output = _serialize_text(
        tmp_path,
        """### FINDING_1: [OUT_OF_SCOPE] Neutral
Vote tally: YES=1 NO=1 Result=neutral
""",
    )
    assert counts == (0, 0)
    assert output == ""


def test_oos_serialize_result_accepted_written(tmp_path: Path) -> None:
    counts, output = _serialize_text(
        tmp_path,
        """### FINDING_1: [OUT_OF_SCOPE] Accepted
Vote tally: YES=3 NO=0 Result=accepted
""",
    )
    assert counts == (1, 0)
    assert "### OOS_1: [OUT_OF_SCOPE] Accepted" in output


def test_oos_serialize_result_token_boundaries(tmp_path: Path) -> None:
    counts, output = _serialize_text(
        tmp_path,
        """### FINDING_1: [OUT_OF_SCOPE] NotResult stays eligible
Vote tally: YES=0 NO=3 NotResult=rejected
### FINDING_2: [OUT_OF_SCOPE] NoResult stays eligible
Vote tally: YES=0 NO=3 NoResult=rejected
### FINDING_3: [OUT_OF_SCOPE] Accepted extra rejected
Vote tally: YES=3 NO=0 Result=accepted-extra
### FINDING_4: [OUT_OF_SCOPE] Accepted trailing space
Vote tally: YES=3 NO=0 Result=accepted 
### FINDING_5: [OUT_OF_SCOPE] Accepted end
Vote tally: YES=3 NO=0 Result=accepted
""",
    )
    assert counts == (4, 0)
    assert "NotResult stays eligible" in output
    assert "NoResult stays eligible" in output
    assert "Accepted extra rejected" not in output
    assert "Accepted trailing space" in output
    assert "Accepted end" in output


def test_oos_serialize_rejected_security_still_held(tmp_path: Path) -> None:
    counts, output = _serialize_text(
        tmp_path,
        """### FINDING_1: [OUT_OF_SCOPE] Security rejected
- **Concern**: focus-area=security secret.
Vote tally: YES=0 NO=3 Result=rejected
### FINDING_2: [OUT_OF_SCOPE] Security neutral
- **Concern**: focus-area=security secret.
Vote tally: YES=1 NO=1 Result=neutral
""",
    )
    assert counts == (0, 2)
    assert output == ""


def test_oos_serialize_prose_result_not_rejected(tmp_path: Path) -> None:
    counts, output = _serialize_text(
        tmp_path,
        """### FINDING_1: [OUT_OF_SCOPE] Prose result
- **Concern**: Mentions Result=rejected in prose.
""",
    )
    assert counts == (1, 0)
    assert "Prose result" in output


def test_oos_serialize_body_cited_security_heading_is_not_security(tmp_path: Path) -> None:
    counts, output = _serialize_text(
        tmp_path,
        """### FINDING_1: [OUT_OF_SCOPE] Body cited heading
- **Concern**: Example follows.
### Example [security] policy
""",
    )
    assert counts == (1, 0)
    assert "Body cited heading" in output


def test_oos_serialize_oos_prefixed_security_header_is_held(tmp_path: Path) -> None:
    counts, output = _serialize_text(
        tmp_path,
        """### FINDING_1: [OOS] `[security]` Header
- **Concern**: hold this.
### FINDING_2: [OOS] `<security>` Angle
- **Concern**: hold this too.
""",
    )
    assert counts == (0, 2)
    assert output == ""


def test_oos_serialize_focus_area_field_normalizes_backticks_and_asterisks(tmp_path: Path) -> None:
    counts, output = _serialize_text(
        tmp_path,
        """### FINDING_1: [OUT_OF_SCOPE] Backtick field
- **focus-area**: `security-hardening`
""",
    )
    assert counts == (0, 1)
    assert output == ""


def test_oos_is_security_tagged_space_separated_focus_area() -> None:
    # The accepted OOS template writes "- **Focus area**: security" (space, bold).
    # _FOCUS_AREA_FIELD_RE must match this form in addition to hyphenated "focus-area".
    block = (
        "### OOS_1: Some finding\n"
        "- **Description**: something\n"
        "- **Focus area**: security\n"
    )
    assert oos.is_security_tagged(block)


def test_oos_serialize_creates_output_parent_directory(tmp_path: Path) -> None:
    findings = _write_findings(tmp_path, "### FINDING_1: [OOS] Parent dir\n")
    output = tmp_path / "missing" / "nested" / "oos.md"
    assert not output.parent.exists()
    assert oos.oos_serialize(findings_file=findings, output_file=output) == (1, 0)
    assert output.exists()


def test_oos_serialize_classifier_failure_no_partial_sink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    findings = _write_findings(
        tmp_path,
        """### FINDING_1: [OUT_OF_SCOPE] Would be written
### FINDING_2: [OUT_OF_SCOPE] Classifier boom
""",
    )
    output = tmp_path / "oos.md"

    def fail_classifier(block_text: str) -> NoReturn:
        _ = block_text
        raise RuntimeError("boom")

    monkeypatch.setattr(oos, "is_security_tagged", fail_classifier)
    assert oos.oos_serialize_main([
        "--findings-file",
        str(findings),
        "--output-file",
        str(output),
    ]) == 2
    assert output.exists()
    assert output.read_text(encoding="utf-8") == ""


def test_oos_serialize_cli_via_subprocess(tmp_path: Path) -> None:
    findings = _write_findings(tmp_path, "### FINDING_1: [OUT_OF_SCOPE] CLI accepted\n")
    output = tmp_path / "oos.md"
    result = _run_cli([
        "oos",
        "serialize",
        "--findings-file",
        str(findings),
        "--output-file",
        str(output),
    ])
    assert result.returncode == 0
    assert result.stdout == "OOS_ACCEPTED=1\nOOS_HELD_SECURITY=0\n"
    assert "### OOS_1: [OUT_OF_SCOPE] CLI accepted" in output.read_text(encoding="utf-8")


def test_oos_serialize_cli_validation_exit_2(tmp_path: Path) -> None:
    findings = _write_findings(tmp_path, "### FINDING_1: [OOS] Payload\n")
    cases = [
        ["oos", "serialize", "--findings-file", str(tmp_path / "missing.md"), "--output-file", str(tmp_path / "out.md")],
        ["oos", "serialize", "--findings-file", str(findings)],
        ["oos", "serialize", "--findings-file", str(findings), "--output-file", str(tmp_path / "out.md"), "--bogus"],
    ]
    for args in cases:
        result = _run_cli(args)
        assert result.returncode == 2
