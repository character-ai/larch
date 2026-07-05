"""Tests for file_oos.py."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from larch.issue import file_oos

REPO_ROOT = Path(__file__).resolve().parents[3]
OOS_ISSUE_CAP_OPERATOR_WARNING = (
    "**⚠ /implement: oos-issue-cap helper failed (exit <N>) — OOS batch NOT filed; "
    "review accepted-OOS Descriptions and re-run with corrected env, or have the items filed manually**"
)


def test_count_non_security_counts_canonical_oos_headers(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text(
        "### OOS_1: Widget\n- **Description**: bug\n- **Phase**: implement\n",
        encoding="utf-8",
    )
    assert file_oos.count_non_security((str(accepted),)) == 1


def test_count_non_security_counts_multiple_blocks(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text(
        "### OOS_1: First\n- **Description**: a\n"
        "### OOS_2: Second\n- **Description**: b\n",
        encoding="utf-8",
    )
    assert file_oos.count_non_security((str(accepted),)) == 2


def test_count_non_security_counts_legacy_tagged_headers(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text(
        "### FINDING_1: [OUT_OF_SCOPE] Legacy tagged block\n"
        "- **Description**: dropped before #3550.\n",
        encoding="utf-8",
    )
    assert file_oos.count_non_security((str(accepted),)) == 1


def test_count_non_security_counts_legacy_trailing_tagged_headers(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text(
        "### FINDING_1: Legacy tagged block [OUT_OF_SCOPE]\n"
        "- **Description**: tag after title matches awk parity.\n",
        encoding="utf-8",
    )
    assert file_oos.count_non_security((str(accepted),)) == 1


def test_count_non_security_counts_legacy_oos_shorthand_header(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text(
        "### FINDING_1: [OOS] Legacy shorthand block\n"
        "- **Description**: tag after title matches awk parity.\n",
        encoding="utf-8",
    )
    assert file_oos.count_non_security((str(accepted),)) == 1


def test_count_non_security_ignores_bare_finding_headers(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text(
        "### FINDING_1: bare in-scope finding\n- **Concern**: stays in scope.\n",
        encoding="utf-8",
    )
    assert file_oos.count_non_security((str(accepted),)) == 0


def test_count_non_security_excludes_security_tagged_legacy_header(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text(
        "### FINDING_1: [OUT_OF_SCOPE] Security item\n"
        "- **focus-area**: security\n",
        encoding="utf-8",
    )
    assert file_oos.count_non_security((str(accepted),)) == 0


def test_count_non_security_excludes_backtick_unbold_security_focus_area(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text(
        "### OOS_1: Security item\n"
        "- `focus-area`: `security-hardening`\n",
        encoding="utf-8",
    )
    assert file_oos.count_non_security((str(accepted),)) == 0


def test_count_non_security_excludes_unbulleted_security_focus_area(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text(
        "### OOS_1: Security item\n"
        "focus-area: security-hardening\n",
        encoding="utf-8",
    )
    assert file_oos.count_non_security((str(accepted),)) == 0


def test_count_non_security_excludes_structured_security_heading(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text(
        "### OOS_1: [security] Security item\n"
        "- **Description**: private routing.\n",
        encoding="utf-8",
    )
    assert file_oos.count_non_security((str(accepted),)) == 0


def test_count_non_security_does_not_treat_body_security_heading_as_tag(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text(
        "### OOS_1: Public item\n"
        "- **Concern**: cites a heading below.\n"
        "### Example [security] policy\n",
        encoding="utf-8",
    )
    assert file_oos.count_non_security((str(accepted),)) == 1


def test_count_non_security_skips_missing_files(tmp_path: Path) -> None:
    assert file_oos.count_non_security((str(tmp_path / "nonexistent.md"),)) == 0


def test_detect_carve_out_forked(tmp_path: Path) -> None:
    status = file_oos.detect(tmp_path, forked=True)
    assert status.carve_out is True
    assert status.non_security_count == 0


def test_detect_carve_out_repo_unavailable(tmp_path: Path) -> None:
    status = file_oos.detect(tmp_path, repo_unavailable=True)
    assert status.carve_out is True


def test_detect_no_oos(tmp_path: Path) -> None:
    status = file_oos.detect(tmp_path)
    assert status.non_security_count == 0
    assert status.already_filed is False
    assert status.carve_out is False


def test_detect_with_accepted_oos(tmp_path: Path) -> None:
    accepted = tmp_path / "oos-accepted-main-agent.md"
    _ = accepted.write_text(
        "### OOS_1: Widget\n- **Description**: bug\n",
        encoding="utf-8",
    )
    status = file_oos.detect(tmp_path)
    assert status.non_security_count == 1
    assert status.already_filed is False


def test_detect_idempotent_when_sentinel_present(tmp_path: Path) -> None:
    sentinel = tmp_path / "oos-issues-created.md"
    _ = sentinel.write_text(
        "Created https://github.com/example/larch/issues/99\n",
        encoding="utf-8",
    )
    status = file_oos.detect(tmp_path)
    assert status.already_filed is True


def test_detect_security_present(tmp_path: Path) -> None:
    sec = tmp_path / "security-oos-observations.md"
    _ = sec.write_text("### OOS_1: sec item\n- **focus-area**: security\n", encoding="utf-8")
    status = file_oos.detect(tmp_path)
    assert status.security_present is True


def test_read_filed_urls_empty_sentinel(tmp_path: Path) -> None:
    assert file_oos.read_filed_urls_from_sentinel(None) == []
    assert file_oos.read_filed_urls_from_sentinel(str(tmp_path / "missing.md")) == []


def test_read_filed_urls_from_sentinel(tmp_path: Path) -> None:
    sentinel = tmp_path / "oos-issues-created.md"
    _ = sentinel.write_text(
        "Created https://github.com/example/larch/issues/10\n"
        "Created https://github.com/example/larch/issues/11\n",
        encoding="utf-8",
    )
    urls = file_oos.read_filed_urls_from_sentinel(str(sentinel))
    assert len(urls) == 2


def test_accepted_oos_paths_returns_canonical_paths(tmp_path: Path) -> None:
    paths = file_oos.accepted_oos_paths(tmp_path)
    assert str(tmp_path / "oos-accepted-review.md") in paths
    assert str(tmp_path / "oos-accepted-main-agent.md") in paths


def test_cli_no_oos(tmp_path: Path) -> None:
    result = file_oos.main(["--tmpdir", str(tmp_path)])
    assert result == 0


def test_cli_with_forked(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _ = file_oos.main(["--tmpdir", str(tmp_path), "--forked"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["carve_out"] is True


def test_design_export_oos_path_resolution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DESIGN_TMPDIR", raising=False)
    exported = tmp_path / "design-export" / "oos-accepted-design.md"
    exported.parent.mkdir()
    _ = exported.write_text("### OOS_1: Exported\n- **Description**: ok\n", encoding="utf-8")
    resolved = file_oos.resolve_design_oos_path(tmp_path)
    assert resolved == exported


def test_design_tmpdir_env_oos_path_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design_dir = tmp_path / "design"
    design_dir.mkdir()
    accepted = design_dir / "oos-accepted-design.md"
    _ = accepted.write_text("### OOS_1: From design tmpdir\n", encoding="utf-8")
    monkeypatch.setenv("DESIGN_TMPDIR", str(design_dir))
    resolved = file_oos.resolve_design_oos_path(tmp_path)
    assert resolved == accepted


def test_disposition_checkpoint_security_sidecar_returns_rc3(tmp_path: Path) -> None:
    _ = (tmp_path / "security-oos-observations.md").write_text("# security observation\n", encoding="utf-8")

    rc = file_oos.disposition_checkpoint_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 3
    assert "security sidecar present" in (tmp_path / "oos-disposition-checkpoint.stderr.log").read_text(encoding="utf-8")


def test_disposition_checkpoint_mixed_security_and_public_returns_rc3_after_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = (tmp_path / "security-oos-observations.md").write_text("# security observation\n", encoding="utf-8")
    _ = (tmp_path / "oos-accepted-main-agent.md").write_text(
        "### OOS_1: Public follow-up\n"
        "- **Description**: File publicly.\n"
        "- **Vote tally**: YES=2 NO=0\n",
        encoding="utf-8",
    )
    run_dir = tmp_path / "larch-logs" / "implement" / "run-1"
    run_dir.mkdir(parents=True)
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")
    _ = (run_dir / "oos-issues.ndjson").write_text(
        '{"body":"Created https://github.com/example/larch/issues/101\\n"}\n',
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_gate(**kwargs: object) -> int:
        seen.update(kwargs)
        return 0

    monkeypatch.setattr(file_oos, "disposition_gate", fake_gate)

    rc = file_oos.disposition_checkpoint_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 3
    assert seen["oos_issues_ndjson"] == run_dir / "oos-issues.ndjson"
    assert "security sidecar present" in (tmp_path / "oos-disposition-checkpoint.stderr.log").read_text(encoding="utf-8")


def test_disposition_checkpoint_mixed_security_and_public_missing_ndjson_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = (tmp_path / "security-oos-observations.md").write_text("# security observation\n", encoding="utf-8")
    _ = (tmp_path / "oos-accepted-main-agent.md").write_text(
        "### OOS_1: Public follow-up\n"
        "- **Description**: File publicly.\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "oos-accepted-review.md").write_text("", encoding="utf-8")
    _ = (tmp_path / "oos-accepted-design.md").write_text("", encoding="utf-8")
    _ = (tmp_path / "ship-pr-state.sh").write_text("FORKED_TARGET=false\nREPO_UNAVAILABLE=false\n", encoding="utf-8")
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")
    (tmp_path / "larch-logs" / "implement" / "run-1").mkdir(parents=True)

    class Result:
        def __init__(self, returncode: int, stdout: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = ""

    def fake_run(argv: list[str], **_kwargs: object) -> Result:
        if argv[:3] == ["git", "merge-base", "HEAD"]:
            return Result(1, "")
        if argv[:4] == ["git", "rev-parse", "--verify", "origin/main"]:
            return Result(0, "abc123\n")
        return Result(0, "")

    def forbidden_gate(**_kwargs: object) -> int:
        raise AssertionError("disposition_gate must not run when oos-issues.ndjson is missing")

    monkeypatch.setattr(file_oos.subprocess, "run", fake_run)
    monkeypatch.setattr(file_oos, "disposition_gate", forbidden_gate)

    rc = file_oos.disposition_checkpoint_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 2
    assert "non-security accepted OOS requires a resolved oos-issues.ndjson path" in (
        tmp_path / "oos-disposition-checkpoint.stderr.log"
    ).read_text(encoding="utf-8")


def test_issue_cap_rejects_malformed_batch(tmp_path: Path) -> None:
    bad = tmp_path / "bad.md"
    _ = bad.write_text("### Item one\n- **Description**: not oos shaped\n", encoding="utf-8")
    with pytest.raises(ValueError, match="OOS-shaped"):
        file_oos.issue_cap(bad)


def append_oos(path: Path, n: int, title: str, description: str) -> None:
    with path.open("a", encoding="utf-8") as handle:
        _ = handle.write(f"### OOS_{n}: {title}\n")
        _ = handle.write(f"- **Description**: {description}\n")
        _ = handle.write("- **Reviewer**: Test\n")
        _ = handle.write("- **Vote tally**: YES=2 NO=0\n")
        _ = handle.write("- **Phase**: implement\n\n")


def make_issue_cap_input(tmp_path: Path, name: str) -> Path:
    path = tmp_path / name / "input.md"
    path.parent.mkdir(parents=True)
    _ = path.write_text("", encoding="utf-8")
    return path


def build_many_issue_cap_oos(path: Path, count: int) -> None:
    _ = path.write_text("", encoding="utf-8")
    for n in range(1, count + 1):
        append_oos(path, n, f"Title {n}", f"Description for item {n} touching skills/foo/item-{n}.sh:{n}-{n + 1}")


def run_issue_cap(
    input_file: Path,
    output: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    repo = Path(__file__).resolve().parents[3]
    merged_env = os.environ.copy()
    _ = merged_env.pop("OOS_ISSUES_PER_RUN_CAP", None)
    if env:
        merged_env.update(env)
    argv = [sys.executable, str(repo / "python" / "cli.py"), "oos", "issue-cap", "--input-file", str(input_file)]
    if output is not None:
        argv.extend(["--output", str(output)])
    return subprocess.run(
        argv,
        cwd=repo,
        env=merged_env,
        text=True,
        capture_output=True,
        check=False,
    )


def assert_issue_cap_heading_count(path: Path, expected: int) -> None:
    text = path.read_text(encoding="utf-8")
    assert len(re.findall(r"^### OOS_\d+:", text, re.MULTILINE)) == expected


@pytest.mark.parametrize(
    ("name", "env", "expected_count", "first_rolled", "last_rolled"),
    [
        ("default_cap_exceeded", {}, 1, 1, 7),
        ("explicit_cap_exceeded", {"OOS_ISSUES_PER_RUN_CAP": "3"}, 3, 3, 7),
    ],
)
def test_issue_cap_exceeded_rolls_surplus(
    tmp_path: Path,
    name: str,
    env: dict[str, str],
    expected_count: int,
    first_rolled: int,
    last_rolled: int,
) -> None:
    src = make_issue_cap_input(tmp_path, name)
    build_many_issue_cap_oos(src, 7)
    out = tmp_path / name / "out.md"

    result = run_issue_cap(src, out, env)

    assert result.returncode == 0
    assert_issue_cap_heading_count(out, expected_count)
    text = out.read_text(encoding="utf-8")
    assert f"### OOS_{expected_count}: Aggregated rollup" in text
    assert "- **Reviewer**: Combined: capped per-run rollup" in text
    assert f"Title {first_rolled}" in text
    assert f"Title {last_rolled}" in text
    assert "rolled up by the per-run OOS issue cap" in text


@pytest.mark.parametrize(
    ("name", "count", "cap"),
    [
        ("under_cap", 3, "5"),
        ("equal_count", 5, "5"),
    ],
)
def test_issue_cap_under_or_equal_cap_passes_through(tmp_path: Path, name: str, count: int, cap: str) -> None:
    src = make_issue_cap_input(tmp_path, name)
    build_many_issue_cap_oos(src, count)
    out = tmp_path / name / "out.md"

    result = run_issue_cap(src, out, {"OOS_ISSUES_PER_RUN_CAP": cap})

    assert result.returncode == 0
    assert out.read_text(encoding="utf-8") == src.read_text(encoding="utf-8")


def test_issue_cap_cap_one_rolls_all_items(tmp_path: Path) -> None:
    src = make_issue_cap_input(tmp_path, "cap-one")
    build_many_issue_cap_oos(src, 4)
    out = tmp_path / "cap-one" / "out.md"

    result = run_issue_cap(src, out, {"OOS_ISSUES_PER_RUN_CAP": "1"})

    assert result.returncode == 0
    text = out.read_text(encoding="utf-8")
    assert_issue_cap_heading_count(out, 1)
    assert "### OOS_1: Aggregated rollup of 4 capped OOS items" in text
    assert "Title 1" in text
    assert "Title 4" in text


def test_issue_cap_empty_input_passes_through(tmp_path: Path) -> None:
    src = make_issue_cap_input(tmp_path, "empty")
    out = tmp_path / "empty" / "out.md"

    result = run_issue_cap(src, out)

    assert result.returncode == 0
    assert out.read_text(encoding="utf-8") == ""


@pytest.mark.parametrize(
    ("name", "env", "stderr_substring"),
    [
        ("invalid_cap_zero", {"OOS_ISSUES_PER_RUN_CAP": "0"}, "OOS_ISSUES_PER_RUN_CAP must be a positive integer"),
        ("invalid_cap_non_numeric", {"OOS_ISSUES_PER_RUN_CAP": "abc"}, "OOS_ISSUES_PER_RUN_CAP must be a positive integer"),
        ("invalid_cap_negative", {"OOS_ISSUES_PER_RUN_CAP": "-1"}, "OOS_ISSUES_PER_RUN_CAP must be a positive integer"),
        ("invalid_cap_empty", {"OOS_ISSUES_PER_RUN_CAP": ""}, "OOS_ISSUES_PER_RUN_CAP must be a positive integer"),
    ],
)
def test_issue_cap_invalid_env_exits_two_without_output(
    tmp_path: Path,
    name: str,
    env: dict[str, str],
    stderr_substring: str,
) -> None:
    src = make_issue_cap_input(tmp_path, name)
    build_many_issue_cap_oos(src, 2)
    out = tmp_path / name / "out.md"

    result = run_issue_cap(src, out, env)

    assert result.returncode == 2
    assert stderr_substring in result.stderr
    assert not out.exists()


def test_issue_cap_warning_string_consistency_in_config_docs() -> None:
    config = (REPO_ROOT / "docs" / "configuration-and-permissions.md").read_text(encoding="utf-8")
    assert OOS_ISSUE_CAP_OPERATOR_WARNING in config


def test_issue_cap_invalid_env_deletes_stale_output(tmp_path: Path) -> None:
    src = make_issue_cap_input(tmp_path, "invalid-env-stale-output")
    build_many_issue_cap_oos(src, 2)
    out = tmp_path / "invalid-env-stale-output" / "out.md"
    _ = out.write_text("stale\n", encoding="utf-8")

    result = run_issue_cap(src, out, {"OOS_ISSUES_PER_RUN_CAP": "0"})

    assert result.returncode == 2
    assert "OOS_ISSUES_PER_RUN_CAP must be a positive integer" in result.stderr
    assert not out.exists()


def test_issue_cap_malformed_no_body_uses_fallback(tmp_path: Path) -> None:
    src = make_issue_cap_input(tmp_path, "malformed-no-body")
    build_many_issue_cap_oos(src, 4)
    with src.open("a", encoding="utf-8") as handle:
        _ = handle.write("### OOS_5: Missing description\n")
        _ = handle.write("- **Reviewer**: Test\n")
        _ = handle.write("- **Vote tally**: YES=2 NO=0\n")
        _ = handle.write("- **Phase**: implement\n\n")
        _ = handle.write("### OOS_6: Last\n")
        _ = handle.write("- **Description**: Final body\n")
        _ = handle.write("- **Reviewer**: Test\n")
        _ = handle.write("- **Vote tally**: YES=2 NO=0\n")
        _ = handle.write("- **Phase**: implement\n\n")
    out = tmp_path / "malformed-no-body" / "out.md"

    result = run_issue_cap(src, out)

    assert result.returncode == 0
    text = out.read_text(encoding="utf-8")
    # A missing Description must fall back to the full raw block, never a placeholder.
    assert "(malformed item — body unavailable)" not in text
    assert "(body unavailable)" not in text
    assert "  - **Missing description**:" in text
    assert "### OOS_5: Missing description" in text


def test_issue_cap_malformed_with_body_preserves_diagnostic(tmp_path: Path) -> None:
    src = make_issue_cap_input(tmp_path, "malformed-with-body")
    build_many_issue_cap_oos(src, 4)
    with src.open("a", encoding="utf-8") as handle:
        _ = handle.write("### OOS_5: Incomplete\n")
        _ = handle.write("- **Description**: Diagnostic body survives for skills/foo/diagnostic.sh:7\n")
        _ = handle.write("### OOS_6: Next\n")
        _ = handle.write("- **Description**: Next body\n")
        _ = handle.write("- **Reviewer**: Test\n")
        _ = handle.write("- **Vote tally**: YES=2 NO=0\n")
        _ = handle.write("- **Phase**: implement\n\n")
    out = tmp_path / "malformed-with-body" / "out.md"

    result = run_issue_cap(src, out)

    assert result.returncode == 0
    text = out.read_text(encoding="utf-8")
    assert "Diagnostic body survives" in text
    assert "[Files: skills/foo/diagnostic.sh:7]" in text


def test_issue_cap_rollup_preserves_full_bodies_verbatim(tmp_path: Path) -> None:
    # Regression for #5097: a capped rollup must embed every combined item's
    # full body verbatim, not a truncated excerpt or a placeholder.
    src = make_issue_cap_input(tmp_path, "full-bodies")
    bodies = {
        1: "Body one with multi-line detail.\n  Continuation line that must survive.",
        2: "Body two referencing skills/x/y.sh:42 and a ``` fence ``` token.",
        3: "Body three " + ("z" * 400),
    }
    for number, body in bodies.items():
        append_oos(src, number, f"Title {number}", body)
    out = tmp_path / "full-bodies" / "out.md"

    result = run_issue_cap(src, out, {"OOS_ISSUES_PER_RUN_CAP": "1"})

    assert result.returncode == 0
    text = out.read_text(encoding="utf-8")
    # Exactly one filed (column-0) OOS block — the aggregate.
    assert len(re.findall(r"^### OOS_\d+:", text, re.MULTILINE)) == 1
    # Every combined item's full body survives, untruncated.
    assert "Continuation line that must survive." in text
    assert "``` fence ```" in text
    assert "z" * 400 in text
    assert "…" not in text
    # The aggregate re-parses as a single filing item carrying all the detail.
    items, _mode = file_oos.parse_issue_input(text)
    assert len(items) == 1
    assert "z" * 400 in items[0].body


def test_issue_cap_in_place_rewrite_matches_explicit_output(tmp_path: Path) -> None:
    src = make_issue_cap_input(tmp_path, "in-place")
    build_many_issue_cap_oos(src, 7)
    copy = tmp_path / "in-place" / "copy.md"
    _ = copy.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    expected = tmp_path / "in-place" / "expected.md"

    explicit = run_issue_cap(copy, expected)
    in_place = run_issue_cap(src)

    assert explicit.returncode == 0
    assert in_place.returncode == 0
    assert src.read_text(encoding="utf-8") == expected.read_text(encoding="utf-8")


def test_issue_cap_renumbers_headings(tmp_path: Path) -> None:
    src = make_issue_cap_input(tmp_path, "renumber")
    append_oos(src, 1, "First", "Body one")
    append_oos(src, 3, "Second", "Body two")
    append_oos(src, 5, "Third", "Body three")
    append_oos(src, 9, "Fourth", "Body four")
    append_oos(src, 11, "Fifth", "Body five")
    append_oos(src, 13, "Sixth", "Body six")
    out = tmp_path / "renumber" / "out.md"

    result = run_issue_cap(src, out, {"OOS_ISSUES_PER_RUN_CAP": "3"})

    assert result.returncode == 0
    headings = re.findall(r"^### (OOS_\d+:)", out.read_text(encoding="utf-8"), re.MULTILINE)
    assert headings == ["OOS_1:", "OOS_2:", "OOS_3:"]


def test_issue_cap_missing_input_fails_closed(tmp_path: Path) -> None:
    out = tmp_path / "missing" / "out.md"
    out.parent.mkdir()

    result = run_issue_cap(tmp_path / "missing" / "input.md", out)

    assert result.returncode == 1
    assert "input file not found" in result.stderr
    assert not out.exists()


def test_issue_cap_failure_deletes_stale_output(tmp_path: Path) -> None:
    src = make_issue_cap_input(tmp_path, "stale-output")
    _ = src.write_text("### Generic first\nBody one\n### Generic second\nBody two\n", encoding="utf-8")
    out = tmp_path / "stale-output" / "out.md"
    _ = out.write_text("stale\n", encoding="utf-8")

    result = run_issue_cap(src, out)

    assert result.returncode == 1
    assert "not OOS-shaped" in result.stderr
    assert not out.exists()


def test_issue_cap_in_place_failure_preserves_input(tmp_path: Path) -> None:
    src = make_issue_cap_input(tmp_path, "in-place-failure")
    _ = src.write_text("### Generic first\nBody one\n### Generic second\nBody two\n", encoding="utf-8")
    before = src.read_bytes()

    result = run_issue_cap(src)

    assert result.returncode == 1
    assert src.read_bytes() == before


def test_issue_cap_same_input_output_path_rejected(tmp_path: Path) -> None:
    src = make_issue_cap_input(tmp_path, "same-path")
    before = src.read_bytes()

    result = run_issue_cap(src, src)

    assert result.returncode == 1
    assert "resolve to the same path" in result.stderr
    assert src.read_bytes() == before


def test_issue_cap_utf8_multibyte_preserved(tmp_path: Path) -> None:
    src = make_issue_cap_input(tmp_path, "utf8")
    build_many_issue_cap_oos(src, 4)
    body = "前缀😀中文字符保持完整 plus trailing prose that is preserved in full"
    append_oos(src, 5, "UTF8", body)
    append_oos(src, 6, "After", "Body after UTF8")
    out = tmp_path / "utf8" / "out.md"

    result = run_issue_cap(src, out)

    assert result.returncode == 0
    text = out.read_text(encoding="utf-8")
    assert "�" not in text
    assert "…" not in text
    assert body in text


def test_issue_cap_markdown_normalization_in_aggregate_bullets(tmp_path: Path) -> None:
    src = make_issue_cap_input(tmp_path, "markdown-normalization")
    build_many_issue_cap_oos(src, 4)
    append_oos(src, 5, "# **`Risky title`", "# excerpt starts like heading with **bold** and `code`")
    append_oos(src, 6, "Normal", "Normal body")
    out = tmp_path / "markdown-normalization" / "out.md"

    result = run_issue_cap(src, out)

    assert result.returncode == 0
    text = out.read_text(encoding="utf-8")
    # The item title bullet is still normalized (no markdown/heading markers).
    assert "  - **Risky title**:" in text
    assert "  - **#" not in text
    # The body is now embedded verbatim, so its markdown survives unmodified.
    assert "with **bold** and `code`" in text


def test_issue_cap_file_reference_preserved_in_rollup(tmp_path: Path) -> None:
    src = make_issue_cap_input(tmp_path, "files-suffix")
    build_many_issue_cap_oos(src, 4)
    long_body = f"{'x' * 80} then mentions skills/foo/bar.sh:200-300"
    append_oos(src, 5, "Path in body", long_body)
    append_oos(src, 6, "After", "Body after path")
    out = tmp_path / "files-suffix" / "out.md"

    result = run_issue_cap(src, out)

    assert result.returncode == 0
    text = out.read_text(encoding="utf-8")
    assert "[Files: skills/foo/bar.sh:200-300]" in text
    assert long_body in text


@pytest.mark.parametrize("cap", ["3", "1"])
def test_issue_cap_parser_heading_parity_mismatch(tmp_path: Path, cap: str) -> None:
    src = make_issue_cap_input(tmp_path, f"parity-{cap}")
    append_oos(src, 1, "First", "Body one")
    with src.open("a", encoding="utf-8") as handle:
        _ = handle.write("### OOS_2: Incomplete\n")
        _ = handle.write("- **Description**: Body before pending heading\n")
        _ = handle.write("### Pending generic\n")
        _ = handle.write("Generic body\n")
        _ = handle.write("### OOS_3: Third\n")
        _ = handle.write("- **Description**: Body three\n")
        _ = handle.write("- **Reviewer**: Test\n")
        _ = handle.write("- **Vote tally**: YES=2 NO=0\n")
        _ = handle.write("- **Phase**: implement\n\n")
    out = tmp_path / f"parity-{cap}" / "out.md"

    result = run_issue_cap(src, out, {"OOS_ISSUES_PER_RUN_CAP": cap})

    assert result.returncode == 1
    assert "ITEMS_TOTAL" in result.stderr
    assert not out.exists()


def test_issue_cap_non_oos_input_rejected(tmp_path: Path) -> None:
    src = make_issue_cap_input(tmp_path, "non-oos")
    _ = src.write_text("### Generic first\nBody one\n### Generic second\nBody two\n", encoding="utf-8")
    out = tmp_path / "non-oos" / "out.md"

    result = run_issue_cap(src, out)

    assert result.returncode == 1
    assert "not OOS-shaped" in result.stderr
    assert not out.exists()


def run_file_conflict_deps(
    input_file: Path,
    output: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    repo = Path(__file__).resolve().parents[3]
    merged_env = os.environ.copy()
    _ = merged_env.pop("OOS_FILE_CONFLICT_CLUSTER_CAP", None)
    _ = merged_env.pop("OOS_FILE_CONFLICT_GLOBAL_CAP", None)
    if env:
        merged_env.update(env)
    return subprocess.run(
        [
            sys.executable,
            str(repo / "python" / "cli.py"),
            "oos",
            "file-conflict-deps",
            "--input-file",
            str(input_file),
            "--output",
            str(output),
        ],
        cwd=repo,
        env=merged_env,
        text=True,
        capture_output=True,
        check=False,
    )


def assert_file_conflict_deps_tsv(output: Path, expected: str) -> None:
    assert output.is_file()
    assert output.read_text(encoding="utf-8") == expected


def make_file_conflict_deps_input(tmp_path: Path, name: str) -> Path:
    path = tmp_path / name / "input.md"
    path.parent.mkdir(parents=True)
    _ = path.write_text("", encoding="utf-8")
    return path


def test_file_conflict_deps_same_file_serialization(tmp_path: Path) -> None:
    src = make_file_conflict_deps_input(tmp_path, "case-a")
    append_oos(src, 1, "First", "Touches skills/foo/bar.sh")
    append_oos(src, 2, "Second", "Also touches skills/foo/bar.sh")
    out = tmp_path / "case-a" / "out.tsv"

    result = run_file_conflict_deps(src, out)

    assert result.returncode == 0
    assert_file_conflict_deps_tsv(out, "1\t2\n")


def test_file_conflict_deps_disjoint_ranges_parallel(tmp_path: Path) -> None:
    src = make_file_conflict_deps_input(tmp_path, "case-b")
    append_oos(src, 1, "First", "Touches skills/foo/bar.sh:1-50")
    append_oos(src, 2, "Second", "Touches skills/foo/bar.sh:200-300")
    out = tmp_path / "case-b" / "out.tsv"

    result = run_file_conflict_deps(src, out)

    assert result.returncode == 0
    assert_file_conflict_deps_tsv(out, "")


def test_file_conflict_deps_overlapping_ranges_conflict(tmp_path: Path) -> None:
    src = make_file_conflict_deps_input(tmp_path, "case-c")
    append_oos(src, 1, "First", "Touches skills/foo/bar.sh:1-100")
    append_oos(src, 2, "Second", "Touches skills/foo/bar.sh:50-150")
    out = tmp_path / "case-c" / "out.tsv"

    result = run_file_conflict_deps(src, out)

    assert result.returncode == 0
    assert_file_conflict_deps_tsv(out, "1\t2\n")


def test_file_conflict_deps_whole_file_fallback_conflicts(tmp_path: Path) -> None:
    src = make_file_conflict_deps_input(tmp_path, "case-d")
    append_oos(src, 1, "First", "Touches skills/foo/bar.sh:1-50")
    append_oos(src, 2, "Second", "Touches skills/foo/bar.sh")
    out = tmp_path / "case-d" / "out.tsv"

    result = run_file_conflict_deps(src, out)

    assert result.returncode == 0
    assert_file_conflict_deps_tsv(out, "1\t2\n")


def test_file_conflict_deps_all_pairs_cluster_under_cap(tmp_path: Path) -> None:
    src = make_file_conflict_deps_input(tmp_path, "case-e")
    append_oos(src, 1, "First", "Touches skills/foo/bar.sh")
    append_oos(src, 2, "Second", "Touches skills/foo/bar.sh")
    append_oos(src, 3, "Third", "Touches skills/foo/bar.sh")
    out = tmp_path / "case-e" / "out.tsv"

    result = run_file_conflict_deps(src, out)

    assert result.returncode == 0
    assert_file_conflict_deps_tsv(out, "1\t2\n1\t3\n2\t3\n")


def test_file_conflict_deps_different_files_parallel(tmp_path: Path) -> None:
    src = make_file_conflict_deps_input(tmp_path, "case-f")
    append_oos(src, 1, "First", "Touches skills/foo/a.sh")
    append_oos(src, 2, "Second", "Touches skills/foo/b.sh")
    out = tmp_path / "case-f" / "out.tsv"

    result = run_file_conflict_deps(src, out)

    assert result.returncode == 0
    assert_file_conflict_deps_tsv(out, "")


def test_file_conflict_deps_rejects_absolute_paths(tmp_path: Path) -> None:
    src = make_file_conflict_deps_input(tmp_path, "case-g")
    append_oos(src, 1, "First", "Mentions /etc/passwd")
    append_oos(src, 2, "Second", "Touches skills/foo/bar.sh")
    out = tmp_path / "case-g" / "out.tsv"

    result = run_file_conflict_deps(src, out)

    assert result.returncode == 0
    assert_file_conflict_deps_tsv(out, "")


def test_file_conflict_deps_same_leading_slash_path_serializes(tmp_path: Path) -> None:
    # Bash parity: clean_match strips a leading slash, so two items citing the
    # same leading-slash path normalize to the same repo-relative path and must
    # serialize (1\t2) rather than running in parallel.
    src = make_file_conflict_deps_input(tmp_path, "case-g2")
    append_oos(src, 1, "First", "Mentions /skills/foo/bar.sh")
    append_oos(src, 2, "Second", "Also mentions /skills/foo/bar.sh")
    out = tmp_path / "case-g2" / "out.tsv"

    result = run_file_conflict_deps(src, out)

    assert result.returncode == 0
    assert_file_conflict_deps_tsv(out, "1\t2\n")


@pytest.mark.parametrize(
    ("name", "path_text"),
    [
        ("dockerfile_subdir", "tools/Dockerfile"),
        ("makefile_subdir", "src/Makefile"),
    ],
)
def test_file_conflict_deps_extensionless_subdir_path_serializes(
    tmp_path: Path, name: str, path_text: str
) -> None:
    # Bash parity: an extensionless match in a subdirectory carries a leading
    # slash from the boundary (e.g. "/Dockerfile"); clean_match strips it, so
    # two items citing the same extensionless path must serialize.
    src = make_file_conflict_deps_input(tmp_path, name)
    append_oos(src, 1, "First", f"Touches {path_text}")
    append_oos(src, 2, "Second", f"Also touches {path_text}")
    out = tmp_path / name / "out.tsv"

    result = run_file_conflict_deps(src, out)

    assert result.returncode == 0
    assert_file_conflict_deps_tsv(out, "1\t2\n")


def test_file_conflict_deps_rejects_traversal_paths(tmp_path: Path) -> None:
    src = make_file_conflict_deps_input(tmp_path, "case-h")
    append_oos(src, 1, "First", "Mentions ../../etc/passwd")
    append_oos(src, 2, "Second", "Touches skills/foo/bar.sh")
    out = tmp_path / "case-h" / "out.tsv"

    result = run_file_conflict_deps(src, out)

    assert result.returncode == 0
    assert_file_conflict_deps_tsv(out, "")


@pytest.mark.parametrize(
    ("name", "path_text"),
    [
        ("case-h2", "../skills/foo.py"),
        ("case-h3", "/../skills/foo/bar.sh"),
    ],
)
def test_file_conflict_deps_rejects_normalized_traversal_paths(
    tmp_path: Path, name: str, path_text: str
) -> None:
    # Regex sub-matches can drop a leading .. prefix before clean_match; two items
    # citing the same traversal-looking path must not serialize as 1\t2.
    src = make_file_conflict_deps_input(tmp_path, name)
    append_oos(src, 1, "First", f"Mentions {path_text}")
    append_oos(src, 2, "Second", f"Also mentions {path_text}")
    out = tmp_path / name / "out.tsv"

    result = run_file_conflict_deps(src, out)

    assert result.returncode == 0
    assert_file_conflict_deps_tsv(out, "")


def test_file_conflict_deps_malformed_item_preserves_index(tmp_path: Path) -> None:
    src = make_file_conflict_deps_input(tmp_path, "case-i")
    append_oos(src, 1, "First", "Touches skills/foo/bar.sh")
    with src.open("a", encoding="utf-8") as handle:
        _ = handle.write("### OOS_2: Malformed\n")
        _ = handle.write("- **Reviewer**: Test\n")
        _ = handle.write("- **Vote tally**: YES=2 NO=0\n")
        _ = handle.write("- **Phase**: implement\n\n")
    append_oos(src, 3, "Third", "Touches skills/foo/bar.sh")
    out = tmp_path / "case-i" / "out.tsv"

    result = run_file_conflict_deps(src, out)

    assert result.returncode == 0
    assert_file_conflict_deps_tsv(out, "1\t3\n")


def test_file_conflict_deps_cluster_chain_degradation(tmp_path: Path) -> None:
    src = make_file_conflict_deps_input(tmp_path, "case-j")
    for n in range(1, 23):
        append_oos(src, n, f"Item {n}", "Touches skills/foo/bar.sh")
    out = tmp_path / "case-j" / "out.tsv"
    expected = "".join(f"{n}\t{n + 1}\n" for n in range(1, 22))

    result = run_file_conflict_deps(src, out)

    assert result.returncode == 0
    assert "N=22" in result.stderr
    assert_file_conflict_deps_tsv(out, expected)


def test_file_conflict_deps_global_cap_failure(tmp_path: Path) -> None:
    src = make_file_conflict_deps_input(tmp_path, "case-k")
    item = 1
    for cluster in range(1, 5):
        for _ in range(4):
            append_oos(src, item, f"Item {item}", f"Touches skills/foo/file-{cluster}.sh")
            item += 1
    out = tmp_path / "case-k" / "out.tsv"

    result = run_file_conflict_deps(src, out, {"OOS_FILE_CONFLICT_CLUSTER_CAP": "3", "OOS_FILE_CONFLICT_GLOBAL_CAP": "10"})

    assert result.returncode == 1
    assert "exceeding the 10-row" in result.stderr
    assert not out.exists()


@pytest.mark.parametrize(
    ("name", "path_text"),
    [
        ("makefile", "Makefile"),
        ("dotfile", ".pre-commit-config.yaml"),
        ("root_long_extension", "agent-lint.toml"),
    ],
)
def test_file_conflict_deps_root_level_path_forms(tmp_path: Path, name: str, path_text: str) -> None:
    src = make_file_conflict_deps_input(tmp_path, name)
    append_oos(src, 1, "First", f"Touches {path_text}")
    append_oos(src, 2, "Second", f"Touches {path_text}")
    out = tmp_path / name / "out.tsv"

    result = run_file_conflict_deps(src, out)

    assert result.returncode == 0
    assert_file_conflict_deps_tsv(out, "1\t2\n")


@pytest.mark.parametrize(
    ("name", "left", "right", "expected"),
    [
        ("reversed_range", "skills/foo/bar.sh:50-1", "skills/foo/bar.sh:60-70", "1\t2\n"),
        ("zero_range", "skills/foo/bar.sh:0-10", "skills/foo/bar.sh:60-70", "1\t2\n"),
        ("adjacent_non_overlap", "skills/foo/bar.sh:1-49", "skills/foo/bar.sh:50-100", ""),
        ("boundary_overlap", "skills/foo/bar.sh:1-50", "skills/foo/bar.sh:50-100", "1\t2\n"),
    ],
)
def test_file_conflict_deps_range_edge_cases(tmp_path: Path, name: str, left: str, right: str, expected: str) -> None:
    src = make_file_conflict_deps_input(tmp_path, name)
    append_oos(src, 1, "First", f"Touches {left}")
    append_oos(src, 2, "Second", f"Touches {right}")
    out = tmp_path / name / "out.tsv"

    result = run_file_conflict_deps(src, out)

    assert result.returncode == 0
    assert_file_conflict_deps_tsv(out, expected)


def test_file_conflict_deps_atomic_tier2_failure(tmp_path: Path) -> None:
    src = make_file_conflict_deps_input(tmp_path, "case-s")
    item = 1
    for cluster in range(1, 5):
        for _ in range(4):
            append_oos(src, item, f"Item {item}", f"Touches skills/foo/atomic-{cluster}.sh")
            item += 1
    out = tmp_path / "case-s" / "out.tsv"

    result = run_file_conflict_deps(src, out, {"OOS_FILE_CONFLICT_CLUSTER_CAP": "3", "OOS_FILE_CONFLICT_GLOBAL_CAP": "10"})

    assert result.returncode == 1
    assert "exceeding the 10-row" in result.stderr
    assert not out.exists()


def test_file_conflict_deps_pending_heading_malformed_parse_case(tmp_path: Path) -> None:
    src = make_file_conflict_deps_input(tmp_path, "case-t")
    append_oos(src, 1, "First", "Touches skills/foo/bar.sh")
    with src.open("a", encoding="utf-8") as handle:
        _ = handle.write("### OOS_2: Incomplete\n")
        _ = handle.write("- **Description**: Touches skills/foo/bar.sh\n")
        _ = handle.write("### Pending generic\n")
        _ = handle.write("Generic body touches skills/foo/other.sh\n")
    append_oos(src, 3, "Third", "Touches skills/foo/bar.sh")
    out = tmp_path / "case-t" / "out.tsv"

    result = run_file_conflict_deps(src, out)

    assert result.returncode == 0
    assert_file_conflict_deps_tsv(out, "1\t4\n")


def test_file_conflict_deps_generic_fallback_body_file_case(tmp_path: Path) -> None:
    src = make_file_conflict_deps_input(tmp_path, "case-u")
    _ = src.write_text(
        "### Generic first\n"
        "Body touches skills/foo/bar.sh\n"
        "### Generic second\n"
        "Body also touches skills/foo/bar.sh\n\n",
        encoding="utf-8",
    )
    out = tmp_path / "case-u" / "out.tsv"

    result = run_file_conflict_deps(src, out)

    assert result.returncode == 0
    assert_file_conflict_deps_tsv(out, "1\t2\n")


@pytest.mark.parametrize(
    ("name", "separator"),
    [("comma_separated_paths", ","), ("semicolon_separated_paths", ";")],
)
def test_file_conflict_deps_adjacent_separated_paths(tmp_path: Path, name: str, separator: str) -> None:
    src = make_file_conflict_deps_input(tmp_path, name)
    append_oos(src, 1, "First", f"Touches skills/foo/a.sh{separator}skills/foo/b.sh")
    append_oos(src, 2, "Second", "Touches skills/foo/b.sh")
    out = tmp_path / name / "out.tsv"

    result = run_file_conflict_deps(src, out)

    assert result.returncode == 0
    assert_file_conflict_deps_tsv(out, "1\t2\n")


def test_file_conflict_deps_cap_failure_deletes_stale_output(tmp_path: Path) -> None:
    src = make_file_conflict_deps_input(tmp_path, "case-x")
    item = 1
    for cluster in range(1, 5):
        for _ in range(4):
            append_oos(src, item, f"Item {item}", f"Touches skills/foo/stale-{cluster}.sh")
            item += 1
    out = tmp_path / "case-x" / "out.tsv"
    _ = out.write_text("STALE\tROW\n", encoding="utf-8")

    result = run_file_conflict_deps(src, out, {"OOS_FILE_CONFLICT_CLUSTER_CAP": "3", "OOS_FILE_CONFLICT_GLOBAL_CAP": "10"})

    assert result.returncode == 1
    assert "exceeding the 10-row" in result.stderr
    assert not out.exists()


def test_file_conflict_deps_input_failure_clears_stale_output(tmp_path: Path) -> None:
    out = tmp_path / "case-pf" / "out.tsv"
    out.parent.mkdir()
    _ = out.write_text("STALE\tROW\n", encoding="utf-8")

    result = run_file_conflict_deps(tmp_path / "case-pf" / "does-not-exist.md", out)

    assert result.returncode == 1
    assert not out.exists()


@pytest.mark.parametrize(
    ("name", "env", "stderr_substring"),
    [
        (
            "invalid_cluster_cap",
            {"OOS_FILE_CONFLICT_CLUSTER_CAP": "abc"},
            "OOS_FILE_CONFLICT_CLUSTER_CAP must be a positive integer",
        ),
        (
            "invalid_global_cap",
            {"OOS_FILE_CONFLICT_GLOBAL_CAP": "0"},
            "OOS_FILE_CONFLICT_GLOBAL_CAP must be a positive integer",
        ),
    ],
)
def test_file_conflict_deps_invalid_cap_exits_2_without_deleting_stale_output(
    tmp_path: Path,
    name: str,
    env: dict[str, str],
    stderr_substring: str,
) -> None:
    src = make_file_conflict_deps_input(tmp_path, name)
    append_oos(src, 1, "First", "Touches skills/foo/a.sh")
    append_oos(src, 2, "Second", "Touches skills/foo/a.sh")
    out = tmp_path / name / "out.tsv"
    _ = out.write_text("STALE\tROW\n", encoding="utf-8")

    result = run_file_conflict_deps(src, out, env)

    assert result.returncode == 2
    assert stderr_substring in result.stderr
    assert out.read_text(encoding="utf-8") == "STALE\tROW\n"


def test_file_conflict_deps_one_edge_per_pair(tmp_path: Path) -> None:
    src = make_file_conflict_deps_input(tmp_path, "one-edge")
    append_oos(src, 1, "First", "Touches skills/foo/a.sh and skills/foo/b.sh")
    append_oos(src, 2, "Second", "Touches skills/foo/a.sh and skills/foo/b.sh")
    out = tmp_path / "one-edge" / "out.tsv"

    result = run_file_conflict_deps(src, out, {"OOS_FILE_CONFLICT_CLUSTER_CAP": "1"})

    assert result.returncode == 0
    assert "would emit" not in result.stderr
    assert_file_conflict_deps_tsv(out, "1\t2\n")


def test_file_conflict_deps_defaults_output_to_implement_tmpdir(tmp_path: Path) -> None:
    src = make_file_conflict_deps_input(tmp_path, "default-output")
    append_oos(src, 1, "First", "Touches skills/foo/a.sh")
    append_oos(src, 2, "Second", "Touches skills/foo/a.sh")
    repo = Path(__file__).resolve().parents[3]
    env = os.environ.copy()
    _ = env.pop("OOS_FILE_CONFLICT_CLUSTER_CAP", None)
    _ = env.pop("OOS_FILE_CONFLICT_GLOBAL_CAP", None)
    env["IMPLEMENT_TMPDIR"] = str(tmp_path / "impl")
    Path(env["IMPLEMENT_TMPDIR"]).mkdir()

    result = subprocess.run(
        [sys.executable, str(repo / "python" / "cli.py"), "oos", "file-conflict-deps", "--input-file", str(src)],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert (Path(env["IMPLEMENT_TMPDIR"]) / "oos-intra-batch-deps.tsv").read_text(encoding="utf-8") == "1\t2\n"


def test_disposition_gate_fails_without_disposition(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text("### OOS_1: Missing\n- **Phase**: implement\n", encoding="utf-8")
    filed = tmp_path / "urls.md"
    _ = filed.write_text("", encoding="utf-8")

    def _inline_zero(_range: str) -> int:
        return 0

    _ = monkeypatch.setattr(file_oos, "_count_inline_triage", _inline_zero)
    rc = file_oos.disposition_gate(
        accepted_files=[accepted],
        filed_url_files=[filed],
        filed_url_strict_files=[],
        commit_range="HEAD",
    )
    assert rc == 1


def test_disposition_gate_passes_with_strict_filed_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text("### OOS_1: Filed\n- **Phase**: implement\n", encoding="utf-8")
    strict = tmp_path / "strict.md"
    _ = strict.write_text("- **Filed URL**: https://github.com/example/larch/issues/99\n", encoding="utf-8")

    def _inline_zero(_range: str) -> int:
        return 0

    _ = monkeypatch.setattr(file_oos, "_count_inline_triage", _inline_zero)
    rc = file_oos.disposition_gate(
        accepted_files=[accepted],
        filed_url_files=[],
        filed_url_strict_files=[strict],
        commit_range="HEAD",
    )
    assert rc == 0


def test_disposition_gate_passes_with_inline_triage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text("### OOS_1: Inline\n- **Phase**: implement\n", encoding="utf-8")
    filed = tmp_path / "urls.md"
    _ = filed.write_text("", encoding="utf-8")

    def _inline_one(_range: str) -> int:
        return 1

    _ = monkeypatch.setattr(file_oos, "_count_inline_triage", _inline_one)
    rc = file_oos.disposition_gate(
        accepted_files=[accepted],
        filed_url_files=[filed],
        filed_url_strict_files=[],
        commit_range="HEAD",
    )
    assert rc == 0


def test_disposition_gate_bypasses_in_fork_mode(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text("### OOS_1: Forked\n- **Phase**: implement\n", encoding="utf-8")
    filed = tmp_path / "urls.md"
    _ = filed.write_text("", encoding="utf-8")
    rc = file_oos.disposition_gate(
        accepted_files=[accepted],
        filed_url_files=[filed],
        filed_url_strict_files=[],
        commit_range="HEAD",
        fork_mode=True,
    )
    assert rc == 0


def test_materialize_manifest_oos_writes_main_agent_file(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    _ = manifest.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "status": "complete",
                "oos_observations": [
                    {"title": "Retain manifest OOS", "description": "Fix docs for manifest OOS.", "phase": "implement"},
                ],
            }
        ),
        encoding="utf-8",
    )
    count = file_oos.materialize_manifest_oos(manifest, tmp_path)
    assert count == 1
    text = (tmp_path / "oos-accepted-main-agent.md").read_text(encoding="utf-8")
    assert "### OOS_1: Retain manifest OOS" in text
    assert "- **Reviewer**: External implementer" in text


def _write_manifest(path: Path, observations: object) -> None:
    _ = path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "status": "complete",
                "oos_observations": observations,
            }
        ),
        encoding="utf-8",
    )


def test_materialize_manifest_oos_empty_array_noops(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest, [])

    assert file_oos.materialize_manifest_oos(manifest, tmp_path) == 0

    assert not (tmp_path / "oos-accepted-main-agent.md").exists()


def test_materialize_manifest_oos_duplicate_title_rerun_is_idempotent(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    _write_manifest(
        manifest,
        [{"title": "Retain manifest OOS", "description": "Fix docs.", "phase": "implement"}],
    )

    assert file_oos.materialize_manifest_oos(manifest, tmp_path) == 1
    assert file_oos.materialize_manifest_oos(manifest, tmp_path) == 1

    text = (tmp_path / "oos-accepted-main-agent.md").read_text(encoding="utf-8")
    assert text.count("### OOS_") == 1


def test_materialize_manifest_oos_count_only_reports_length(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = tmp_path / "manifest.json"
    _write_manifest(
        manifest,
        [{"title": "Counted", "description": "x", "phase": "implement", "focus_area": "correctness"}],
    )

    assert file_oos.materialize_manifest_oos(manifest, tmp_path, count_only=True) == 1
    assert (
        file_oos.materialize_manifest_main(
            ["--count-only", "--manifest-path", str(manifest), "--implement-tmpdir", str(tmp_path)]
        )
        == 0
    )
    assert capsys.readouterr().out == "1\n"
    assert file_oos.materialize_manifest_oos(manifest, tmp_path) == 1

    assert "- **focus-area**: correctness" in (tmp_path / "oos-accepted-main-agent.md").read_text(encoding="utf-8")


def test_materialize_manifest_oos_invalid_top_level_type_cli_fails(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest, "bad")

    rc = file_oos.materialize_manifest_main(
        ["--count-only", "--manifest-path", str(manifest), "--implement-tmpdir", str(tmp_path)]
    )

    assert rc == 1
    assert "oos_observations must be an array" in capsys.readouterr().err


def test_materialize_manifest_oos_scalar_item_full_path_fails_closed(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest, ["bad"])

    with pytest.raises(TypeError, match=r"oos_observations\[1\] must be a JSON object"):
        _ = file_oos.materialize_manifest_oos(manifest, tmp_path)

    public = tmp_path / "oos-accepted-main-agent.md"
    assert not public.exists()


def test_materialize_manifest_oos_count_only_allows_mixed_item_shapes(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest, [{"title": "x"}, "bad"])

    assert file_oos.materialize_manifest_oos(manifest, tmp_path, count_only=True) == 2


def test_materialize_manifest_oos_routes_structured_security_and_dedupes_exact_titles(
    tmp_path: Path,
) -> None:
    audit = tmp_path / "security-oos-observations.md"
    _ = audit.write_text("### Security OOS: Token leak followup\n", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    _write_manifest(
        manifest,
        [
            {
                "title": "Token leak",
                "description": "Private details.",
                "phase": "implement",
                "focus_area": "security-privacy",
            }
        ],
    )

    assert file_oos.materialize_manifest_oos(manifest, tmp_path) == 1
    assert file_oos.materialize_manifest_oos(manifest, tmp_path) == 1

    audit_text = audit.read_text(encoding="utf-8")
    assert "### Security OOS: Token leak followup" in audit_text
    assert audit_text.splitlines().count("### Security OOS: Token leak") == 1
    assert not (tmp_path / "oos-accepted-main-agent.md").read_text(encoding="utf-8").strip()
    assert "cli.py oos materialize-manifest" in (tmp_path / "execution-issues.md").read_text(encoding="utf-8")


def test_materialize_manifest_oos_security_prose_and_title_alone_remain_public(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.json"
    _write_manifest(
        manifest,
        [
            {
                "title": "Security title only",
                "description": "Description says focus-area = security as prose.",
                "phase": "review",
            },
            {
                "title": "Security hardening",
                "description": "- **focus-area**: security-hardening\nPrivate details.",
                "phase": "implement",
            },
        ],
    )

    assert file_oos.materialize_manifest_oos(manifest, tmp_path) == 2

    public = (tmp_path / "oos-accepted-main-agent.md").read_text(encoding="utf-8")
    assert "### OOS_1: Security title only" in public
    assert "Security hardening" not in public
    audit = (tmp_path / "security-oos-observations.md").read_text(encoding="utf-8")
    assert "### Security OOS: Security hardening" in audit
    assert "Security title only" not in audit


def test_materialize_manifest_oos_missing_redactor_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest, [{"title": "Needs scrub", "description": "token text"}])
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path / "missing-plugin-root"))

    with pytest.raises(RuntimeError, match="redact secrets missing or not executable"):
        _ = file_oos.materialize_manifest_oos(manifest, tmp_path)


def test_materialize_manifest_oos_monotonic_oos_numbering(tmp_path: Path) -> None:
    _ = (tmp_path / "oos-accepted-main-agent.md").write_text(
        "### OOS_1: Existing item\n- **Description**: Existing.\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest, [{"title": "New monotonic item", "description": "Append.", "phase": "review"}])

    assert file_oos.materialize_manifest_oos(manifest, tmp_path) == 1

    assert "### OOS_2: New monotonic item" in (tmp_path / "oos-accepted-main-agent.md").read_text(
        encoding="utf-8"
    )


def test_materialize_manifest_oos_title_injection_and_pii_redaction(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    _write_manifest(
        manifest,
        [
            {
                "title": "Injected\n### OOS_99: forged",
                "description": (
                    "Contact admin@example.com, call 415-555-1212, use SSN 123-45-6789, "
                    "tenant_ABCDEF123456, http://service.internal/path, "
                    "http://10.1.2.3/path, http://fc00::1/path, and http://fe80::1/path."
                ),
                "phase": "implement",
            },
            {"title": "Injected ### OOS_99: forged", "description": "duplicate after title normalization"},
            {"title": "", "description": "No title."},
        ],
    )

    assert file_oos.materialize_manifest_oos(manifest, tmp_path) == 3

    text = (tmp_path / "oos-accepted-main-agent.md").read_text(encoding="utf-8")
    headings = [line for line in text.splitlines() if line.startswith("### OOS_")]
    assert len(headings) == 2
    assert not any(line.startswith("### OOS_99:") for line in headings)
    assert text.count("<INTERNAL-URL>") >= 4
    assert "<REDACTED-PII>" in text
    assert "admin@example.com" not in text
    assert "415-555-1212" not in text
    assert "123-45-6789" not in text
    assert "tenant_ABCDEF123456" not in text
    assert "http://service.internal/path" not in text
    assert "http://10.1.2.3/path" not in text
    assert "http://fc00::1/path" not in text
    assert "http://fe80::1/path" not in text
    assert "### OOS_2: Untitled external implementer OOS 3" in text


def test_materialize_manifest_oos_redactor_failure_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest, [{"title": "Secret", "description": "raw secret text"}])

    def fail_redact(_text: str) -> str:
        raise RuntimeError("redactor failed")

    monkeypatch.setattr(file_oos, "redact", fail_redact)

    with pytest.raises(RuntimeError, match="redactor failed"):
        _ = file_oos.materialize_manifest_oos(manifest, tmp_path)

    public = tmp_path / "oos-accepted-main-agent.md"
    assert not public.exists() or "raw secret text" not in public.read_text(encoding="utf-8")


def test_disposition_checkpoint_uses_origin_main_when_merge_base_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _ = (tmp_path / "ship-pr-state.sh").write_text("FORKED_TARGET=false\nREPO_UNAVAILABLE=false\n", encoding="utf-8")
    _ = (tmp_path / "oos-accepted-main-agent.md").write_text("### OOS_1: Missing\n- **Phase**: implement\n", encoding="utf-8")
    _ = (tmp_path / "oos-accepted-review.md").write_text("", encoding="utf-8")
    _ = (tmp_path / "oos-accepted-design.md").write_text("", encoding="utf-8")
    run_dir = tmp_path / "larch-logs" / "implement" / "run-1"
    run_dir.mkdir(parents=True)
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")
    _ = (run_dir / "oos-issues.ndjson").write_text("", encoding="utf-8")

    class Result:
        def __init__(self, returncode: int, stdout: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = ""

    def fake_run(argv: list[str], **_kwargs: object) -> Result:
        if argv[:3] == ["git", "merge-base", "HEAD"]:
            return Result(1, "")
        if argv[:4] == ["git", "rev-parse", "--verify", "origin/main"]:
            return Result(0, "abc123\n")
        return Result(0, "")

    seen: dict[str, str] = {}

    def fake_gate(**kwargs: object) -> int:
        seen["commit_range"] = str(kwargs["commit_range"])
        return 0

    _ = monkeypatch.setattr(file_oos.subprocess, "run", fake_run)
    _ = monkeypatch.setattr(file_oos, "disposition_gate", fake_gate)
    rc = file_oos.disposition_checkpoint_main(["--implement-tmpdir", str(tmp_path)])
    assert rc == 0
    assert seen["commit_range"] == "origin/main..HEAD"


def test_disposition_gate_orphan_ndjson_without_accepted_file(tmp_path: Path) -> None:
    ndjson = tmp_path / "orphan.ndjson"
    _ = ndjson.write_text('{"body":"Created https://github.com/example/larch/issues/404\\n"}\n', encoding="utf-8")
    rc = file_oos.disposition_gate_main(
        [
            "--accepted-files",
            f"{tmp_path}/missing-a.md,{tmp_path}/missing-b.md",
            "--filed-urls-file",
            str(tmp_path / "empty-urls.md"),
            "--oos-issues-ndjson",
            str(ndjson),
            "--commit-range",
            "HEAD",
        ],
    )
    assert rc == 2


def test_disposition_gate_security_only_passes_without_urls(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    accepted = tmp_path / "sec.md"
    _ = accepted.write_text(
        "### OOS_1: Secret thing\n- **focus-area**: security\n- **Phase**: implement\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "empty-urls.md").write_text("", encoding="utf-8")
    _ = monkeypatch.setattr(file_oos, "_count_inline_triage", lambda _commit_range: 0)  # type: ignore[arg-type]
    rc = file_oos.disposition_gate_main(
        [
            "--accepted-files",
            str(accepted),
            "--filed-urls-file",
            str(tmp_path / "empty-urls.md"),
            "--commit-range",
            "HEAD",
        ],
    )
    assert rc == 0


def test_disposition_gate_non_security_without_disposition_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    accepted = tmp_path / "bad.md"
    _ = accepted.write_text("### OOS_1: Orphan\n- **Description**: bug\n", encoding="utf-8")
    _ = (tmp_path / "empty-urls.md").write_text("", encoding="utf-8")
    _ = monkeypatch.setattr(file_oos, "_count_inline_triage", lambda _commit_range: 0)  # type: ignore[arg-type]
    rc = file_oos.disposition_gate_main(
        [
            "--accepted-files",
            str(accepted),
            "--filed-urls-file",
            str(tmp_path / "empty-urls.md"),
            "--commit-range",
            "HEAD",
        ],
    )
    assert rc == 1


def test_read_kv_file_missing_symlink_follow_and_crlf_strip(tmp_path: Path) -> None:
    missing = tmp_path / "missing.env"
    assert not file_oos._read_kv_file(missing)  # pyright: ignore[reportPrivateUsage]

    target = tmp_path / "target.env"
    _ = target.write_bytes(b"A=one\r\nB=two\r\n")
    link = tmp_path / "link.env"
    link.symlink_to(target)

    assert file_oos._read_kv_file(link) == {"A": "one", "B": "two"}  # pyright: ignore[reportPrivateUsage]
