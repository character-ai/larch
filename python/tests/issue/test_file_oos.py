"""Tests for file_oos.py."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

from larch.core import config
from larch.issue import file_oos

if TYPE_CHECKING:
    import pytest

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


def test_parse_oos_blocks_stops_at_intervening_finding_heading() -> None:
    text = (
        "### OOS_1: first\n"
        "first body\n"
        "### FINDING_2: middle\n"
        "finding body\n"
        "### OOS_3: last\n"
        "last body\n"
    )

    blocks = file_oos._parse_oos_blocks(text)  # pyright: ignore[reportPrivateUsage]

    assert [(block.number, block.body) for block in blocks] == [
        (1, "### OOS_1: first\nfirst body"),
        (3, "### OOS_3: last\nlast body"),
    ]


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




def assert_issue_cap_heading_count(path: Path, expected: int) -> None:
    text = path.read_text(encoding="utf-8")
    assert len(re.findall(r"^### OOS_\d+:", text, re.MULTILINE)) == expected












def test_issue_cap_warning_string_consistency_in_config_docs() -> None:
    config = (REPO_ROOT / "docs" / "configuration-and-permissions.md").read_text(encoding="utf-8")
    assert OOS_ISSUE_CAP_OPERATOR_WARNING in config
































def test_validate_issue_cap_excludes_fenced_oos_headings_under_shared_helper() -> None:
    text = (
        "### OOS_1: Real\n"
        "- **Description**: Before fence\n"
        "```markdown\n"
        "### OOS_99: Fenced phantom\n"
        "```\n"
        "- **Phase**: implement\n"
        "### OOS_2: Also real\n"
        "- **Description**: After\n"
        "~~~\n"
        "### OOS_88: Tilde phantom\n"
        "~~~\n"
    )
    items = file_oos._validate_issue_cap_input(text)  # pyright: ignore[reportPrivateUsage]
    assert [item.title for item in items] == ["Real", "Also real"]






def test_file_conflict_default_global_cap_uses_shared_issue_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OOS_FILE_CONFLICT_CLUSTER_CAP", raising=False)
    monkeypatch.delenv("OOS_FILE_CONFLICT_GLOBAL_CAP", raising=False)

    assert (
        file_oos._file_conflict_caps()[1]  # pyright: ignore[reportPrivateUsage]
        == config.ISSUE_INTRA_BATCH_DEPS_MAX_ROWS
    )


def assert_file_conflict_deps_tsv(output: Path, expected: str) -> None:
    assert output.is_file()
    assert output.read_text(encoding="utf-8") == expected


def make_file_conflict_deps_input(tmp_path: Path, name: str) -> Path:
    path = tmp_path / name / "input.md"
    path.parent.mkdir(parents=True)
    _ = path.write_text("", encoding="utf-8")
    return path
































































































def test_read_kv_file_missing_symlink_follow_and_crlf_strip(tmp_path: Path) -> None:
    missing = tmp_path / "missing.env"
    assert not file_oos._read_kv_file(missing)  # pyright: ignore[reportPrivateUsage]

    target = tmp_path / "target.env"
    _ = target.write_bytes(b"A=one\r\nB=two\r\n")
    link = tmp_path / "link.env"
    link.symlink_to(target)

    assert file_oos._read_kv_file(link) == {"A": "one", "B": "two"}  # pyright: ignore[reportPrivateUsage]


# ---------------------------------------------------------------------------
# Disposition gate / checkpoint parity (ported from test-oos-disposition-gate.sh)
# ---------------------------------------------------------------------------










































































































