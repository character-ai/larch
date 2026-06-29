# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false
"""Tests for version_bump.py."""

from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from larch.core import config
from larch.core import proc
from larch.release import version_bump
from larch.errors import ShipError, Stalled
from larch.core.proc import CommandResult


class ProcRunner:
    """Adapt proc.run to the Runner protocol for integration tests."""

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        check: bool = False,
        stdout: int | None = None,
        stderr: int | None = None,
    ) -> CommandResult:
        return proc.run(
            argv,
            timeout=timeout,
            cwd=cwd,
            env=env,
            check=check,
            stdout=stdout,
            stderr=stderr,
        )



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





def test_classify_deleted_skill_major(tmp_path: Path) -> None:
    repo = _init_bump_repo(tmp_path)
    skill = repo / "skills/base/SKILL.md"
    _ = subprocess.run(["git", "rm", "-q", str(skill.relative_to(repo))], cwd=repo, check=True)
    _ = subprocess.run(["git", "commit", "-q", "-m", "remove base skill"], cwd=repo, check=True)
    result = version_bump.classify_bump(ProcRunner(), cwd=str(repo))
    assert result.bump_type == "MAJOR"
    assert any("Deleted" in reason for reason in result.major_reasons)





def _classify_stub(
    *,
    head_subject: str = "Feature",
    transparent_chain: list[tuple[str, list[str]]] | None = None,
    name_status: str = "",
    merge_base: str = "base1234567890",
) -> StubRunner:
    """Build StubRunner for classify_bump idempotency / diff edges."""
    responses: dict[tuple[str, ...], CommandResult] = {
        ("git", "fetch", "origin", "main", "--quiet"): CommandResult(
            ("git", "fetch", "origin", "main", "--quiet"), 0, "", "", 0.01
        ),
        ("git", "merge-base", "origin/main", "HEAD"): CommandResult(
            ("git", "merge-base", "origin/main", "HEAD"), 0, f"{merge_base}\n", "", 0.01
        ),
        ("git", "log", "-1", "--format=%s", "HEAD"): CommandResult(
            ("git", "log", "-1", "--format=%s", "HEAD"), 0, f"{head_subject}\n", "", 0.01
        ),
        (
            "git",
            "diff",
            "-M",
            "--name-status",
            merge_base,
            "HEAD",
            "--",
            "skills",
            "agents",
        ): CommandResult(
            (
                "git",
                "diff",
                "-M",
                "--name-status",
                merge_base,
                "HEAD",
                "--",
                "skills",
                "agents",
            ),
            0,
            name_status,
            "",
            0.01,
        ),
    }
    chain = transparent_chain or []
    for depth, (subject, files) in enumerate(chain):
        ref = "HEAD" if depth == 0 else f"HEAD~{depth}"
        responses[("git", "rev-parse", ref)] = CommandResult(
            ("git", "rev-parse", ref), 0, f"sha{depth}\n", "", 0.01
        )
        responses[("git", "log", "-1", "--format=%s", ref)] = CommandResult(
            ("git", "log", "-1", "--format=%s", ref), 0, f"{subject}\n", "", 0.01
        )
        file_lines = "\n".join(files) + ("\n" if files else "")
        responses[
            ("git", "diff-tree", "--no-commit-id", "--name-only", "-r", ref)
        ] = CommandResult(
            ("git", "diff-tree", "--no-commit-id", "--name-only", "-r", ref),
            0,
            file_lines,
            "",
            0.01,
        )
    if not chain:
        responses[("git", "rev-parse", "HEAD")] = CommandResult(
            ("git", "rev-parse", "HEAD"), 0, "sha0\n", "", 0.01
        )
        responses[
            ("git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD")
        ] = CommandResult(
            ("git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"),
            0,
            "",
            "",
            0.01,
        )
    else:
        next_ref = f"HEAD~{len(chain)}"
        responses[("git", "rev-parse", next_ref)] = CommandResult(
            ("git", "rev-parse", next_ref), 1, "", "", 0.01
        )
        responses[("git", "log", "-1", "--format=%s", next_ref)] = CommandResult(
            ("git", "log", "-1", "--format=%s", next_ref), 0, head_subject, "", 0.01
        )
    return StubRunner(responses)






def test_extract_frontmatter_requires_exact_delimiters() -> None:
    assert version_bump._extract_frontmatter(" ---\nname: x\n---\n") == ""  # pyright: ignore[reportPrivateUsage]
    assert version_bump._extract_frontmatter("---\nname: x\n---\n") == "name: x"  # pyright: ignore[reportPrivateUsage]


def test_classify_added_skill_minor(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    plugin = repo / ".claude-plugin"
    _ = plugin.mkdir(parents=True)
    _ = (plugin / "plugin.json").write_text('{"version":"1.0.0"}\n', encoding="utf-8")
    runner = _classify_stub(name_status="A\tskills/new/SKILL.md\n")
    result = version_bump.classify_bump(runner, cwd=str(repo))
    assert result.bump_type == "MINOR"


def test_classify_explicit_head_uses_compare_ref_not_worktree_head(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    plugin = repo / ".claude-plugin"
    _ = plugin.mkdir(parents=True)
    _ = (plugin / "plugin.json").write_text('{"version":"1.2.3"}\n', encoding="utf-8")
    runner = StubRunner(
        {
            ("git", "rev-parse", "v1.2.2^{commit}"): CommandResult(("git", "rev-parse", "v1.2.2^{commit}"), 0, "base-sha\n", "", 0.01),
            ("git", "rev-parse", "origin/main^{commit}"): CommandResult(("git", "rev-parse", "origin/main^{commit}"), 0, "head-sha\n", "", 0.01),
            ("git", "show", f"head-sha:{config.PLUGIN_JSON_PATH}"): CommandResult(("git", "show", f"head-sha:{config.PLUGIN_JSON_PATH}"), 0, '{"version":"1.2.3"}\n', "", 0.01),
            ("git", "rev-parse", "head-sha"): CommandResult(("git", "rev-parse", "head-sha"), 0, "head-sha\n", "", 0.01),
            ("git", "log", "-1", "--format=%s", "head-sha"): CommandResult(("git", "log", "-1", "--format=%s", "head-sha"), 0, "Add new skill\n", "", 0.01),
            ("git", "diff-tree", "--no-commit-id", "--name-only", "-r", "head-sha"): CommandResult(("git", "diff-tree", "--no-commit-id", "--name-only", "-r", "head-sha"), 0, "skills/new/SKILL.md\n", "", 0.01),
            ("git", "diff", "-M", "--name-status", "base-sha", "head-sha", "--", "skills", "agents"): CommandResult(("git", "diff", "-M", "--name-status", "base-sha", "head-sha", "--", "skills", "agents"), 0, "A\tskills/new/SKILL.md\n", "", 0.01),
        },
    )
    result = version_bump.classify_bump(runner, cwd=str(repo), base_ref="v1.2.2", head_ref="origin/main")
    assert result.current_version == "1.2.3"
    assert result.bump_type == "MINOR"


def test_classify_explicit_head_rejects_worktree_version_mismatch(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    plugin = repo / ".claude-plugin"
    _ = plugin.mkdir(parents=True)
    _ = (plugin / "plugin.json").write_text('{"version":"1.2.4"}\n', encoding="utf-8")
    runner = StubRunner(
        {
            ("git", "rev-parse", "origin/main^{commit}"): CommandResult(("git", "rev-parse", "origin/main^{commit}"), 0, "head-sha\n", "", 0.01),
            ("git", "show", f"head-sha:{config.PLUGIN_JSON_PATH}"): CommandResult(("git", "show", f"head-sha:{config.PLUGIN_JSON_PATH}"), 0, '{"version":"1.2.3"}\n', "", 0.01),
        },
    )
    with pytest.raises(ShipError, match=r"worktree plugin\.json version"):
        _ = version_bump.classify_bump(runner, cwd=str(repo), head_ref="origin/main")


def test_classify_diff_failure_raises_ship_error(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    plugin = repo / ".claude-plugin"
    _ = plugin.mkdir(parents=True)
    _ = (plugin / "plugin.json").write_text('{"version":"1.0.0"}\n', encoding="utf-8")
    runner = _classify_stub()
    diff_key = (
        "git",
        "diff",
        "-M",
        "--name-status",
        "base1234567890",
        "HEAD",
        "--",
        "skills",
        "agents",
    )
    runner.responses[diff_key] = CommandResult(diff_key, 1, "", "fatal", 0.01)
    with pytest.raises(ShipError, match="git diff"):
        _ = version_bump.classify_bump(runner, cwd=str(repo))


def test_classify_renamed_skill_major(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    plugin = repo / ".claude-plugin"
    _ = plugin.mkdir(parents=True)
    _ = (plugin / "plugin.json").write_text('{"version":"1.0.0"}\n', encoding="utf-8")
    runner = _classify_stub(
        name_status="R100\tskills/old/SKILL.md\tskills/new/SKILL.md\n",
    )
    result = version_bump.classify_bump(runner, cwd=str(repo))
    assert result.bump_type == "MAJOR"


def test_classify_modified_argument_hint_minor(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    plugin = repo / ".claude-plugin"
    _ = plugin.mkdir(parents=True)
    _ = (plugin / "plugin.json").write_text('{"version":"1.0.0"}\n', encoding="utf-8")
    old_fm = "---\nname: x\nargument-hint: [--a]\n---\n"
    new_fm = "---\nname: x\nargument-hint: [--a --b]\n---\n"
    runner = StubRunner(
        {
            ("git", "fetch", "origin", "main", "--quiet"): CommandResult(
                ("git", "fetch", "origin", "main", "--quiet"), 0, "", "", 0.01
            ),
            ("git", "merge-base", "origin/main", "HEAD"): CommandResult(
                ("git", "merge-base", "origin/main", "HEAD"), 0, "base\n", "", 0.01
            ),
            ("git", "log", "-1", "--format=%s", "HEAD"): CommandResult(
                ("git", "log", "-1", "--format=%s", "HEAD"), 0, "work\n", "", 0.01
            ),
            ("git", "rev-parse", "HEAD"): CommandResult(
                ("git", "rev-parse", "HEAD"), 0, "sha\n", "", 0.01
            ),
            (
                "git",
                "diff",
                "-M",
                "--name-status",
                "base",
                "HEAD",
                "--",
                "skills",
                "agents",
            ): CommandResult(
                (
                    "git",
                    "diff",
                    "-M",
                    "--name-status",
                    "base",
                    "HEAD",
                    "--",
                    "skills",
                    "agents",
                ),
                0,
                "M\tskills/x/SKILL.md\n",
                "",
                0.01,
            ),
            ("git", "show", "base:skills/x/SKILL.md"): CommandResult(
                ("git", "show", "base:skills/x/SKILL.md"), 0, old_fm, "", 0.01
            ),
            ("git", "show", "HEAD:skills/x/SKILL.md"): CommandResult(
                ("git", "show", "HEAD:skills/x/SKILL.md"), 0, new_fm, "", 0.01
            ),
        },
    )
    result = version_bump.classify_bump(runner, cwd=str(repo))
    assert result.bump_type == "MINOR"
