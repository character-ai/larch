# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false
"""Tests for version_bump.py."""

from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from larch.core import config
from larch.release import version_bump
from larch.errors import Stalled
from larch.core.proc import CommandResult


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
        stdout: int | None = None,  # pylint: disable=unused-argument
        stderr: int | None = None,  # pylint: disable=unused-argument
    ) -> CommandResult:
        key = tuple(argv)
        if key in self.responses:
            return self.responses[key]
        if (
            len(key) >= 3
            and key[0] == "git"
            and key[1] == "status"
            and key[2] == "--porcelain"
        ):
            short = ("git", "status", "--porcelain")
            if short in self.responses:
                return self.responses[short]
        msg = f"unexpected argv: {argv}"
        raise AssertionError(msg)


def _parse_kv(stdout: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            out[key] = value
    return out


def _init_bump_repo(tmp_path: Path) -> Path:
    _ = tmp_path.mkdir(parents=True, exist_ok=True)
    repo = tmp_path / "repo"
    _ = repo.mkdir()
    _ = subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    _ = subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo, check=True)
    _ = subprocess.run(["git", "config", "user.name", "T"], cwd=repo, check=True)
    plugin = repo / ".claude-plugin"
    _ = plugin.mkdir(parents=True)
    _ = (plugin / "plugin.json").write_text('{"version":"1.2.2"}\n', encoding="utf-8")
    skills = repo / "skills/base"
    _ = skills.mkdir(parents=True)
    _ = (skills / "SKILL.md").write_text("---\nname: base\n---\n", encoding="utf-8")
    _ = (repo / "README.md").write_text("base\n", encoding="utf-8")
    _ = subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    _ = subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)
    _ = subprocess.run(["git", "checkout", "-q", "-b", "feature"], cwd=repo, check=True)
    return repo





def test_apply_bump_error_redaction() -> None:
    home_path = "/Users/secret/larch6/skills/foo/SKILL.md"
    runner = StubRunner(
        {
            ("git", "status", "--porcelain"): CommandResult(
                ("git", "status", "--porcelain"),
                0,
                f"UU {home_path}\n",
                "",
                0.01,
            ),
        },
    )
    result = version_bump.apply_bump(runner=runner, new_version="1.0.1")
    assert "/Users/secret" not in result.error


def test_bump_branch_guard_matrix() -> None:
    version_bump.bump_branch_guard(branch_name="feat", current_branch="feat", forked=False)
    with pytest.raises(Stalled):
        version_bump.bump_branch_guard(branch_name="", current_branch="feat", forked=False)
    with pytest.raises(Stalled):
        version_bump.bump_branch_guard(branch_name="feat", current_branch="other", forked=False)
    with pytest.raises(Stalled):
        version_bump.bump_branch_guard(branch_name="main", current_branch="main", forked=False)
    with pytest.raises(Stalled):
        version_bump.bump_branch_guard(branch_name="master", current_branch="master", forked=False)
    version_bump.bump_branch_guard(branch_name="main", current_branch="main", forked=True)
    version_bump.bump_branch_guard(branch_name="master", current_branch="master", forked=True)




def test_apply_unmerged_returns_not_stalled() -> None:
    runner = StubRunner(
        {
            ("git", "status", "--porcelain"): CommandResult(
                ("git", "status", "--porcelain"),
                0,
                "UU file.txt\n",
                "",
                0.01,
            ),
        },
    )
    result = version_bump.apply_bump(runner=runner, new_version="1.0.1")
    assert result.applied is False
    assert "unmerged" in result.error













def test_apply_status_failure_returns_apply_result() -> None:
    runner = StubRunner(
        {
            ("git", "status", "--porcelain"): CommandResult(
                ("git", "status", "--porcelain"), 128, "", "fatal", 0.01
            ),
        },
    )
    result = version_bump.apply_bump(runner=runner, new_version="1.0.1")
    assert result.applied is False
    assert "git status failed" in result.error


def test_apply_git_add_failure_rolls_back(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _ = repo.mkdir()
    plugin = repo / ".claude-plugin"
    _ = plugin.mkdir(parents=True)
    plugin_json = plugin / "plugin.json"
    _ = plugin_json.write_text('{"version": "1.0.0"}\n', encoding="utf-8")

    runner = StubRunner(
        {
            ("git", "status", "--porcelain"): CommandResult(
                ("git", "status", "--porcelain"), 0, "", "", 0.01
            ),
            ("git", "rev-parse", "--absolute-git-dir"): CommandResult(
                ("git", "rev-parse", "--absolute-git-dir"), 128, "", "not a git repository", 0.01
            ),
            ("git", "add", "--", config.PLUGIN_JSON_PATH): CommandResult(
                ("git", "add", "--", config.PLUGIN_JSON_PATH), 1, "", "fatal", 0.01
            ),
            ("git", "reset", "HEAD", config.PLUGIN_JSON_PATH): CommandResult(
                ("git", "reset", "HEAD", config.PLUGIN_JSON_PATH), 0, "", "", 0.01
            ),
        },
    )
    result = version_bump.apply_bump(runner=runner, new_version="1.0.1", cwd=str(repo))
    assert result.applied is False
    assert "add" in result.error.lower()
    assert plugin_json.read_text(encoding="utf-8") == '{"version": "1.0.0"}\n'
    assert not (plugin_json.with_suffix(plugin_json.suffix + ".bump-backup")).exists()


def test_apply_error_redacts_home_path() -> None:
    home_path = "/Users/secret/larch6/skills/foo/SKILL.md"
    runner = StubRunner(
        {
            ("git", "status", "--porcelain"): CommandResult(
                ("git", "status", "--porcelain"),
                0,
                f"UU {home_path}\n",
                "",
                0.01,
            ),
        },
    )
    result = version_bump.apply_bump(runner=runner, new_version="1.0.1")
    assert result.applied is False
    assert "/Users/secret" not in result.error
    assert config.REDACTED_OPERATOR_REPO in result.error



def test_git_commit_argv_includes_message(tmp_path: Path) -> None:
    runner = StubRunner(
        {
            ("git", "status", "--porcelain"): CommandResult(
                ("git", "status", "--porcelain"), 0, "", "", 0.01
            ),
            ("git", "fetch", "origin", "main", "--quiet"): CommandResult(
                ("git", "fetch", "origin", "main", "--quiet"), 0, "", "", 0.01
            ),
            ("git", "show", "origin/main:.claude-plugin/plugin.json"): CommandResult(
                ("git", "show", "origin/main:.claude-plugin/plugin.json"),
                0,
                '{"version":"0.0.0"}\n',
                "",
                0.01,
            ),
            ("git", "add", "--", config.PLUGIN_JSON_PATH): CommandResult(
                ("git", "add", "--", config.PLUGIN_JSON_PATH), 0, "", "", 0.01
            ),
            (
                "git",
                "commit",
                "-m",
                config.BUMP_COMMIT_SUBJECT_TEMPLATE.format(version="1.0.1"),
            ): CommandResult(
                (
                    "git",
                    "commit",
                    "-m",
                    config.BUMP_COMMIT_SUBJECT_TEMPLATE.format(version="1.0.1"),
                ),
                0,
                "",
                "",
                0.01,
            ),
            ("git", "rev-parse", "HEAD"): CommandResult(
                ("git", "rev-parse", "HEAD"), 0, "sha\n", "", 0.01
            ),
            ("git", "reset", "HEAD", config.PLUGIN_JSON_PATH): CommandResult(
                ("git", "reset", "HEAD", config.PLUGIN_JSON_PATH), 0, "", "", 0.01
            ),
        },
    )
    repo = tmp_path / "repo"
    _ = repo.mkdir()
    plugin = repo / ".claude-plugin"
    _ = plugin.mkdir(parents=True, exist_ok=True)
    _ = (plugin / "plugin.json").write_text('{"version":"1.0.0"}\n', encoding="utf-8")
    result = version_bump.apply_bump(runner=runner, new_version="1.0.1", cwd=str(repo))
    assert result.applied is True
