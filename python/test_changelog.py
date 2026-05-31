"""Tests for changelog.py."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

import proc
import changelog
from changelog import ChangelogError, ChangelogFormat
from proc import CommandResult


class ProcRunner:
    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        check: bool = False,
    ) -> CommandResult:
        return proc.run(argv, timeout=timeout, cwd=cwd, env=env, check=check)

REPO_ROOT = Path(__file__).resolve().parents[1]
LIB_CHANGELOG = REPO_ROOT / "scripts/lib-changelog.sh"
AUTO_RESOLVE = REPO_ROOT / "scripts/auto-resolve-changelog.sh"
COMMIT_CHANGELOG = REPO_ROOT / "scripts/commit-changelog.sh"
DROP_CHANGELOG = REPO_ROOT / "scripts/drop-changelog-commit.sh"

MD_SAMPLE = """\
# Changelog

## [Unreleased]

### Changed

- Pending

and this project adheres to [Semantic Versioning].

## [1.0.0] - 2026-01-01

### Fixed

- Old
"""

RST_SAMPLE = """\
Changelog
=========

Unreleased
----------

Changed
~~~~~~~

- Pending

Version 1.0.0 (2026-01-01)
--------------------------

Fixed
~~~~~

- Old
"""


@dataclass
class StubRunner:
    responses: dict[tuple[str, ...], CommandResult]

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,  # pylint: disable=unused-argument
        cwd: str | None = None,  # pylint: disable=unused-argument
        env: Mapping[str, str] | None = None,  # pylint: disable=unused-argument
        check: bool = False,  # pylint: disable=unused-argument
    ) -> CommandResult:
        key = tuple(argv)
        if key not in self.responses:
            msg = f"unexpected argv: {argv}"
            raise AssertionError(msg)
        return self.responses[key]


def test_first_version_heading_md() -> None:
    assert changelog.first_version_heading(MD_SAMPLE, fmt=ChangelogFormat.MARKDOWN) == "1.0.0"


def test_duplicate_count_md() -> None:
    text = MD_SAMPLE + "\n## [1.0.0] - 2026-02-02\n"
    assert changelog.duplicate_version_heading_count(text, "1.0.0", fmt=ChangelogFormat.MARKDOWN) == 2


@pytest.mark.skipif(
    not LIB_CHANGELOG.is_file() or shutil.which("bash") is None,
    reason="lib-changelog.sh or bash unavailable",
)
def test_parity_extract_version_body_md(tmp_path: Path) -> None:
    path = tmp_path / "CHANGELOG.md"
    _ = path.write_text(MD_SAMPLE, encoding="utf-8")
    dest = tmp_path / "body.md"
    script = (
        f'source "{LIB_CHANGELOG}"\n'
        'changelog_extract_version_body "1.0.0" "$1" CHANGELOG.md\n'
    )
    bash = subprocess.run(
        ["bash", "-c", script, str(dest)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert bash.returncode == 0
    py = changelog.extract_version_body(MD_SAMPLE, "1.0.0", fmt=ChangelogFormat.MARKDOWN)
    assert py == dest.read_text(encoding="utf-8").rstrip("\n")


def test_extract_blank_returns_none() -> None:
    text = "# Changelog\n\n## [1.0.0] - 2026-01-01\n\n"
    assert changelog.extract_version_body(text, "1.0.0", fmt=ChangelogFormat.MARKDOWN) is None


def test_write_entry_no_anchor_raises() -> None:
    with pytest.raises(ChangelogError) as exc:
        _ = changelog.write_changelog_entry(
            "# Changelog\n\nNo anchor here.\n",
            "2.0.0",
            "### Changed\n\n- x\n",
            fmt=ChangelogFormat.MARKDOWN,
        )
    assert exc.value.code == 3


def test_write_entry_inserts_under_unreleased() -> None:
    out = changelog.write_changelog_entry(
        MD_SAMPLE,
        "1.1.0",
        "### Added\n\n- Feature\n",
        fmt=ChangelogFormat.MARKDOWN,
    )
    assert "## [1.1.0]" in out
    assert "### Added" in out


def test_drop_section_md() -> None:
    out = changelog.drop_version_section(MD_SAMPLE, "1.0.0", fmt=ChangelogFormat.MARKDOWN)
    assert "## [1.0.0]" not in out


def test_rst_write_and_drop() -> None:
    out = changelog.write_changelog_entry(
        RST_SAMPLE,
        "1.1.0",
        "Added\n~~~~~\n\n- Feature\n",
        fmt=ChangelogFormat.RST,
    )
    assert "Version 1.1.0" in out
    dropped = changelog.drop_version_section(out, "1.1.0", fmt=ChangelogFormat.RST)
    assert "Version 1.1.0" not in dropped


def test_detect_format_by_extension() -> None:
    assert changelog.detect_format("x", path="CHANGELOG.md") == ChangelogFormat.MARKDOWN
    assert changelog.detect_format("x", path="NEWS.rst") == ChangelogFormat.RST


@pytest.mark.skipif(
    not LIB_CHANGELOG.is_file() or shutil.which("bash") is None,
    reason="lib-changelog.sh or bash unavailable",
)
def test_parity_first_version_heading(tmp_path: Path) -> None:
    path = tmp_path / "CHANGELOG.md"
    _ = path.write_text(MD_SAMPLE, encoding="utf-8")
    script = (
        f'source "{LIB_CHANGELOG}"\n'
        "changelog_first_version_heading CHANGELOG.md\n"
    )
    bash = subprocess.run(
        ["bash", "-c", script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if bash.returncode != 0:
        pytest.skip("lib-changelog.sh awk match() capture needs gawk (macOS awk fails)")
    py = changelog.first_version_heading(MD_SAMPLE, fmt=ChangelogFormat.MARKDOWN)
    assert py == bash.stdout.strip()


@pytest.mark.skipif(
    not COMMIT_CHANGELOG.is_file() or shutil.which("bash") is None,
    reason="commit-changelog.sh or bash unavailable",
)
def test_parity_commit_changelog_idempotent(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _ = repo.mkdir()
    changelog_md = repo / "CHANGELOG.md"
    _ = changelog_md.write_text(MD_SAMPLE, encoding="utf-8")
    bash = subprocess.run(
        ["bash", str(COMMIT_CHANGELOG), "--version", "9.9.9"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    py = changelog.commit_changelog(ProcRunner(), "9.9.9", cwd=str(repo))
    bash_kv: dict[str, str] = {}
    for line in bash.stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            bash_kv[k] = v
    assert str(py.committed).lower() == bash_kv.get("COMMITTED", "").lower()


@pytest.mark.skipif(
    not DROP_CHANGELOG.is_file() or shutil.which("bash") is None,
    reason="drop-changelog-commit.sh or bash unavailable",
)
def test_parity_drop_changelog_noop(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _ = repo.mkdir()
    _ = (repo / "CHANGELOG.md").write_text(MD_SAMPLE, encoding="utf-8")
    bash = subprocess.run(
        ["bash", str(DROP_CHANGELOG), "--version", "1.0.0"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    py = changelog.drop_changelog_commit(ProcRunner(), "1.0.0", cwd=str(repo))
    bash_kv: dict[str, str] = {}
    for line in bash.stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            bash_kv[k] = v
    assert str(py.dropped).lower() == bash_kv.get("DROPPED", "").lower()


@pytest.mark.skipif(
    not AUTO_RESOLVE.is_file() or shutil.which("bash") is None,
    reason="auto-resolve-changelog.sh or bash unavailable",
)
def test_parity_auto_resolve_markdown_fixture(tmp_path: Path) -> None:
    ours = """# Changelog

## Unreleased

### Changed

- Base

## [1.0.0]

### Fixed

- Old
"""
    theirs = """# Changelog

## Unreleased

### Changed

- Base
- Branch

## [1.0.0]

### Fixed

- Old
"""
    path = tmp_path / "CHANGELOG.md"
    _ = path.write_text("", encoding="utf-8")

    runner = StubRunner(
        {
            ("git", "show", ":2:CHANGELOG.md"): CommandResult(
                ("git", "show", ":2:CHANGELOG.md"), 0, ours, "", 0.01
            ),
            ("git", "show", ":3:CHANGELOG.md"): CommandResult(
                ("git", "show", ":3:CHANGELOG.md"), 0, theirs, "", 0.01
            ),
        },
    )
    assert changelog.auto_resolve(runner, "CHANGELOG.md", cwd=str(tmp_path)) is True
    merged = path.read_text(encoding="utf-8")
    assert "- Branch" in merged
    assert "- Base" in merged


def test_rst_duplicate_version_heading_count() -> None:
    assert (
        changelog.duplicate_version_heading_count(
            RST_SAMPLE,
            "1.0.0",
            fmt=ChangelogFormat.RST,
        )
        >= 1
    )


def test_rst_first_version_heading() -> None:
    assert changelog.first_version_heading(RST_SAMPLE, fmt=ChangelogFormat.RST) == "1.0.0"


def test_rst_auto_resolve_blank_before_second_section() -> None:
    ours = """Changelog
=========

Unreleased
----------

- Base

Version 1.0.0 (2026-01-01)
--------------------------

- Tail line

Version 2.0.0 (2026-02-02)
--------------------------

- Next
"""
    theirs = """Changelog
=========

Unreleased
----------

- Base

- Branch

Version 1.0.0 (2026-01-01)
--------------------------

- Tail line

Version 2.0.0 (2026-02-02)
--------------------------

- Next
"""
    ours_lines: list[str] = ours.splitlines()
    theirs_lines: list[str] = theirs.splitlines()
    merged = changelog._auto_resolve_rst(ours_lines, theirs_lines)  # pyright: ignore[reportPrivateUsage]
    assert merged is not None
    assert "- Tail line" in "\n".join(merged)
    assert "- Branch" in "\n".join(merged)


def test_duplicate_count_rst_ignores_subsections() -> None:
    text = RST_SAMPLE + "\nChanged\n~~~~~\n\n- not a version\n"
    assert changelog.duplicate_version_heading_count(text, "1.0.0", fmt=ChangelogFormat.RST) == 1


def test_commit_changelog_uses_only_path(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _ = repo.mkdir()
    _ = (repo / "CHANGELOG.md").write_text(MD_SAMPLE, encoding="utf-8")
    runner = StubRunner(
        {
            ("git", "status", "--porcelain", "--untracked-files=no"): CommandResult(
                ("git", "status", "--porcelain", "--untracked-files=no"), 0, "", "", 0.01
            ),
            ("git", "diff", "--quiet", "--", "CHANGELOG.md"): CommandResult(
                ("git", "diff", "--quiet", "--", "CHANGELOG.md"), 1, "", "", 0.01
            ),
            ("git", "diff", "--cached", "--quiet", "--", "CHANGELOG.md"): CommandResult(
                ("git", "diff", "--cached", "--quiet", "--", "CHANGELOG.md"), 1, "", "", 0.01
            ),
            ("git", "add", "CHANGELOG.md"): CommandResult(
                ("git", "add", "CHANGELOG.md"), 0, "", "", 0.01
            ),
            ("git", "commit", "-m", "Update CHANGELOG for 9.9.9", "--only", "CHANGELOG.md"): CommandResult(
                ("git", "commit", "-m", "Update CHANGELOG for 9.9.9", "--only", "CHANGELOG.md"),
                0,
                "",
                "",
                0.01,
            ),
            ("git", "rev-parse", "HEAD"): CommandResult(
                ("git", "rev-parse", "HEAD"), 0, "deadbeef\n", "", 0.01
            ),
        },
    )
    result = changelog.commit_changelog(runner, "9.9.9", cwd=str(repo))
    assert result.committed is True


@pytest.mark.skipif(
    not LIB_CHANGELOG.is_file() or shutil.which("bash") is None,
    reason="lib-changelog.sh or bash unavailable",
)
def test_parity_duplicate_count_md(tmp_path: Path) -> None:
    path = tmp_path / "CHANGELOG.md"
    text = MD_SAMPLE + "\n## [1.0.0] - 2026-02-02\n"
    _ = path.write_text(text, encoding="utf-8")
    script = (
        f'source "{LIB_CHANGELOG}"\n'
        'changelog_duplicate_version_heading_count "1.0.0" CHANGELOG.md\n'
    )
    bash = subprocess.run(
        ["bash", "-c", script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    py = changelog.duplicate_version_heading_count(text, "1.0.0", fmt=ChangelogFormat.MARKDOWN)
    assert py == int(bash.stdout.strip())


@pytest.mark.skipif(
    not COMMIT_CHANGELOG.is_file() or shutil.which("bash") is None,
    reason="commit-changelog.sh or bash unavailable",
)
def test_parity_commit_changelog_twin_repos(tmp_path: Path) -> None:
    repo_bash = tmp_path / "bash"
    repo_py = tmp_path / "py"
    for repo in (repo_bash, repo_py):
        _ = repo.mkdir()
        _ = subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        _ = subprocess.run(["git", "config", "user.email", "t@e.com"], cwd=repo, check=True)
        _ = subprocess.run(["git", "config", "user.name", "T"], cwd=repo, check=True)
        _ = (repo / "CHANGELOG.md").write_text(MD_SAMPLE, encoding="utf-8")
        _ = subprocess.run(["git", "add", "CHANGELOG.md"], cwd=repo, check=True)
        _ = subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)
    bash = subprocess.run(
        ["bash", str(COMMIT_CHANGELOG), "--version", "8.8.8"],
        cwd=repo_bash,
        capture_output=True,
        text=True,
        check=False,
    )
    py = changelog.commit_changelog(ProcRunner(), "8.8.8", cwd=str(repo_py))
    bash_kv = {k: v for line in bash.stdout.splitlines() if "=" in line for k, v in [line.split("=", 1)]}
    assert bash_kv.get("COMMITTED", "").lower() == str(py.committed).lower()
    if py.committed:
        assert py.commit_sha
