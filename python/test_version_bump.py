"""Tests for version_bump.py."""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

import config
import proc
import version_bump
from errors import Stalled
from proc import CommandResult


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
    ) -> CommandResult:
        return proc.run(argv, timeout=timeout, cwd=cwd, env=env, check=check)

REPO_ROOT = Path(__file__).resolve().parents[1]
CLASSIFY_SH = REPO_ROOT / ".claude/skills/bump-version/scripts/classify-bump.sh"
APPLY_SH = REPO_ROOT / ".claude/skills/bump-version/scripts/apply-bump.sh"
CHECK_SH = REPO_ROOT / "scripts/check-bump-version.sh"
DROP_SH = REPO_ROOT / "scripts/drop-bump-commit.sh"


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


def test_bump_branch_guard_matrix() -> None:
    version_bump.bump_branch_guard("feat", "feat", forked=False)
    with pytest.raises(Stalled):
        version_bump.bump_branch_guard("", "feat", forked=False)
    with pytest.raises(Stalled):
        version_bump.bump_branch_guard("feat", "other", forked=False)
    with pytest.raises(Stalled):
        version_bump.bump_branch_guard("main", "main", forked=False)
    version_bump.bump_branch_guard("main", "main", forked=True)


def test_apply_same_version_race_retries(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _ = repo.mkdir()
    plugin = repo / ".claude-plugin"
    _ = plugin.mkdir(parents=True)
    plugin_json = plugin / "plugin.json"
    _ = plugin_json.write_text('{"version": "1.0.0"}\n', encoding="utf-8")

    calls: list[str] = []

    class RaceRunner:
        def run(
            self,
            argv: Sequence[str],
            *,
            timeout: float | None = None,
            cwd: str | None = None,  # pylint: disable=unused-argument
            env: Mapping[str, str] | None = None,
            check: bool = False,
        ) -> CommandResult:
            _ = timeout, cwd, env, check
            key = " ".join(argv)
            calls.append(key)
            if len(argv) >= 3 and argv[0] == "git" and argv[1] == "status":
                return CommandResult(tuple(argv), 0, "", "", 0.01)
            if len(argv) >= 4 and argv[:4] == ["git", "fetch", "origin", "main"]:
                return CommandResult(tuple(argv), 0, "", "", 0.01)
            if len(argv) >= 3 and argv[0] == "git" and argv[1] == "show" and "origin/main" in argv[2]:
                return CommandResult(tuple(argv), 0, '{"version":"1.0.1"}\n', "", 0.01)
            if len(argv) >= 3 and argv[0] == "git" and argv[1] == "add":
                return CommandResult(tuple(argv), 0, "", "", 0.01)
            if len(argv) >= 3 and argv[0] == "git" and argv[1] == "commit":
                return CommandResult(tuple(argv), 0, "", "", 0.01)
            if len(argv) >= 3 and argv[0] == "git" and argv[1] == "rev-parse":
                return CommandResult(tuple(argv), 0, "deadbeef\n", "", 0.01)
            if len(argv) >= 4 and argv[:4] == ["git", "reset", "HEAD", config.PLUGIN_JSON_PATH]:
                return CommandResult(tuple(argv), 0, "", "", 0.01)
            msg = f"unexpected: {argv}"
            raise AssertionError(msg)

    result = version_bump.apply_bump(RaceRunner(), "1.0.1", cwd=str(repo))
    assert result.applied is True
    assert result.new_version == "1.0.2"
    assert calls.count("git fetch origin main --quiet") >= 2


def test_apply_regression_correction(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _ = repo.mkdir()
    plugin = repo / ".claude-plugin"
    _ = plugin.mkdir(parents=True)
    plugin_json = plugin / "plugin.json"
    _ = plugin_json.write_text('{"version": "1.0.0"}\n', encoding="utf-8")

    class RegressionRunner:
        def run(
            self,
            argv: Sequence[str],
            *,
            timeout: float | None = None,
            cwd: str | None = None,  # pylint: disable=unused-argument
            env: Mapping[str, str] | None = None,
            check: bool = False,
        ) -> CommandResult:
            _ = timeout, cwd, env, check
            if len(argv) >= 3 and argv[0] == "git" and argv[1] == "status":
                return CommandResult(tuple(argv), 0, "", "", 0.01)
            if len(argv) >= 4 and argv[:4] == ["git", "fetch", "origin", "main"]:
                return CommandResult(tuple(argv), 0, "", "", 0.01)
            if len(argv) >= 3 and argv[0] == "git" and argv[1] == "show" and "origin/main" in argv[2]:
                return CommandResult(tuple(argv), 0, '{"version":"2.0.0"}\n', "", 0.01)
            if len(argv) >= 3 and argv[0] == "git" and argv[1] == "add":
                return CommandResult(tuple(argv), 0, "", "", 0.01)
            if len(argv) >= 3 and argv[0] == "git" and argv[1] == "commit":
                return CommandResult(tuple(argv), 0, "", "", 0.01)
            if len(argv) >= 3 and argv[0] == "git" and argv[1] == "rev-parse":
                return CommandResult(tuple(argv), 0, "cafebabe\n", "", 0.01)
            if len(argv) >= 4 and argv[:4] == ["git", "reset", "HEAD", config.PLUGIN_JSON_PATH]:
                return CommandResult(tuple(argv), 0, "", "", 0.01)
            msg = f"unexpected: {argv}"
            raise AssertionError(msg)

    # Target 1.0.1 is behind origin 2.0.0 — PATCH re-inferred from (1.0.0, 1.0.1) lands on 2.0.0
    result = version_bump.apply_bump(RegressionRunner(), "1.0.1", cwd=str(repo))
    assert result.applied is True
    assert result.new_version == "2.0.1"


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
    result = version_bump.apply_bump(runner, "1.0.1")
    assert result.applied is False
    assert "unmerged" in result.error


def test_verify_fail_closed_on_missing_main() -> None:
    runner = StubRunner(
        {
            ("git", "rev-parse", "main"): CommandResult(
                ("git", "rev-parse", "main"), 1, "", "", 0.01
            ),
            ("git", "rev-parse", "origin/main"): CommandResult(
                ("git", "rev-parse", "origin/main"), 1, "", "", 0.01
            ),
        },
    )
    verify = version_bump.verify_bump_commit_count(runner, 0)
    assert verify.verified is False
    assert verify.status == "missing_main_ref"


def test_check_pre_arms_sentinel(tmp_path: Path) -> None:
    skill = tmp_path / ".claude/skills/bump-version/SKILL.md"
    _ = skill.parent.mkdir(parents=True)
    _ = skill.write_text("skill\n", encoding="utf-8")
    impl = tmp_path / "impl"
    _ = impl.mkdir()
    runner = StubRunner(
        {
            ("git", "rev-parse", "main"): CommandResult(
                ("git", "rev-parse", "main"), 0, "abc\n", "", 0.01
            ),
            ("git", "rev-list", "--count", "main..HEAD"): CommandResult(
                ("git", "rev-list", "--count", "main..HEAD"), 0, "2\n", "", 0.01
            ),
        },
    )
    pre = version_bump.check_bump_version_pre(
        runner,
        cwd=str(tmp_path),
        implement_tmpdir=str(impl),
    )
    assert pre.has_bump is True
    assert pre.commits_before == 2
    assert (impl / config.BUMP_VERSION_ARMED_SENTINEL).is_file()


def _init_bump_repo(tmp_path: Path) -> Path:
    _ = tmp_path.mkdir(parents=True, exist_ok=True)
    repo = tmp_path / "repo"
    _ = repo.mkdir()
    _ = subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    _ = subprocess.run(
        ["git", "config", "user.email", "t@example.com"],
        cwd=repo,
        check=True,
    )
    _ = subprocess.run(["git", "config", "user.name", "T"], cwd=repo, check=True)
    plugin = repo / ".claude-plugin"
    _ = plugin.mkdir(parents=True)
    _ = (plugin / "plugin.json").write_text('{"version":"1.2.2"}\n', encoding="utf-8")
    skills = repo / "skills/base"
    _ = skills.mkdir(parents=True)
    _ = (skills / "SKILL.md").write_text("---\nname: base\n---\n", encoding="utf-8")
    _ = (repo / "CHANGELOG.md").write_text("# Changelog\n\n## [1.2.2]\n", encoding="utf-8")
    _ = (repo / "README.md").write_text("base\n", encoding="utf-8")
    _ = subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    _ = subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)
    _ = subprocess.run(["git", "checkout", "-q", "-b", "feature"], cwd=repo, check=True)
    return repo


@pytest.mark.skipif(
    not CLASSIFY_SH.is_file() or shutil.which("bash") is None,
    reason="classify-bump.sh or bash unavailable",
)
def test_parity_classify_none_on_head_bump(tmp_path: Path) -> None:
    repo = _init_bump_repo(tmp_path)
    plugin = repo / ".claude-plugin/plugin.json"
    _ = plugin.write_text('{"version":"1.2.3"}\n', encoding="utf-8")
    _ = subprocess.run(["git", "add", plugin], cwd=repo, check=True)
    _ = subprocess.run(["git", "commit", "-q", "-m", "Bump version to 1.2.3"], cwd=repo, check=True)

    bash = subprocess.run(
        ["bash", str(CLASSIFY_SH)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    runner = ProcRunner()
    py = version_bump.classify_bump(runner, cwd=str(repo))
    bash_kv = _parse_kv(bash.stdout)
    assert py.bump_type == bash_kv.get("BUMP_TYPE")
    assert py.new_version == bash_kv.get("NEW_VERSION")


@pytest.mark.skipif(
    not CHECK_SH.is_file() or shutil.which("bash") is None,
    reason="check-bump-version.sh or bash unavailable",
)
def test_parity_check_bump_pre(tmp_path: Path) -> None:
    repo = _init_bump_repo(tmp_path)
    skill = repo / ".claude/skills/bump-version/SKILL.md"
    _ = skill.parent.mkdir(parents=True, exist_ok=True)
    _ = skill.write_text("# bump\n", encoding="utf-8")
    bash = subprocess.run(
        ["bash", str(CHECK_SH), "--mode", "pre"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    py = version_bump.check_bump_version_pre(ProcRunner(), cwd=str(repo))
    bash_kv = _parse_kv(bash.stdout)
    assert str(py.has_bump).lower() == bash_kv.get("HAS_BUMP", "").lower()
    assert str(py.commits_before) == bash_kv.get("COMMITS_BEFORE")
    assert py.status == bash_kv.get("STATUS")


@pytest.mark.skipif(
    not APPLY_SH.is_file() or shutil.which("bash") is None,
    reason="apply-bump.sh or bash unavailable",
)
def test_parity_apply_bump_clean_repo(tmp_path: Path) -> None:
    repo_bash = _init_bump_repo(tmp_path / "bash")
    repo_py = _init_bump_repo(tmp_path / "py")
    bash = subprocess.run(
        ["bash", str(APPLY_SH), "--new-version", "1.2.3"],
        cwd=repo_bash,
        capture_output=True,
        text=True,
        check=False,
    )
    py = version_bump.apply_bump(ProcRunner(), "1.2.3", cwd=str(repo_py))
    bash_kv = _parse_kv(bash.stdout)
    assert str(py.applied).lower() == bash_kv.get("APPLIED", "").lower()


@pytest.mark.skipif(
    not DROP_SH.is_file() or shutil.which("bash") is None,
    reason="drop-bump-commit.sh or bash unavailable",
)
def test_parity_drop_bump_noop_without_commit(tmp_path: Path) -> None:
    repo = _init_bump_repo(tmp_path)
    bash = subprocess.run(
        ["bash", str(DROP_SH)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    py = version_bump.drop_bump_commit(ProcRunner(), cwd=str(repo))
    bash_kv = _parse_kv(bash.stdout)
    assert str(py.dropped).lower() == bash_kv.get("DROPPED", "").lower()


def test_drop_empty_larch_bump_files_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_bump_repo(tmp_path)
    plugin = repo / ".claude-plugin/plugin.json"
    _ = plugin.write_text('{"version":"2.0.0"}\n', encoding="utf-8")
    _ = subprocess.run(["git", "add", plugin], cwd=repo, check=True)
    _ = subprocess.run(["git", "commit", "-q", "-m", "Bump version to 2.0.0"], cwd=repo, check=True)
    monkeypatch.setenv(config.ENV_LARCH_BUMP_FILES, "::")
    result = version_bump.drop_bump_commit(ProcRunner(), cwd=str(repo))
    assert result.dropped is False
    assert "empty" in result.error.lower()


def test_drop_status_failure_refuses() -> None:
    runner = StubRunner(
        {
            ("git", "status", "--porcelain", "--untracked-files=no"): CommandResult(
                ("git", "status", "--porcelain", "--untracked-files=no"),
                128,
                "",
                "fatal",
                0.01,
            ),
        },
    )
    result = version_bump.drop_bump_commit(runner)
    assert result.dropped is False
    assert "status" in result.error.lower()


def test_verify_git_error_on_rev_list_failure() -> None:
    runner = StubRunner(
        {
            ("git", "rev-parse", "main"): CommandResult(
                ("git", "rev-parse", "main"), 0, "abc\n", "", 0.01
            ),
            ("git", "rev-list", "--count", "main..HEAD"): CommandResult(
                ("git", "rev-list", "--count", "main..HEAD"), 1, "", "fatal", 0.01
            ),
        },
    )
    verify = version_bump.verify_bump_commit_count(runner, 0)
    assert verify.verified is False
    assert verify.status == "git_error"


def test_apply_status_failure_returns_apply_result() -> None:
    runner = StubRunner(
        {
            ("git", "status", "--porcelain"): CommandResult(
                ("git", "status", "--porcelain"), 128, "", "fatal", 0.01
            ),
        },
    )
    result = version_bump.apply_bump(runner, "1.0.1")
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
            ("git", "add", config.PLUGIN_JSON_PATH): CommandResult(
                ("git", "add", config.PLUGIN_JSON_PATH), 1, "", "fatal", 0.01
            ),
            ("git", "reset", "HEAD", config.PLUGIN_JSON_PATH): CommandResult(
                ("git", "reset", "HEAD", config.PLUGIN_JSON_PATH), 0, "", "", 0.01
            ),
        },
    )
    result = version_bump.apply_bump(runner, "1.0.1", cwd=str(repo))
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
    result = version_bump.apply_bump(runner, "1.0.1")
    assert result.applied is False
    assert "/Users/secret" not in result.error
    assert config.REDACTED_OPERATOR_REPO in result.error


def test_apply_max_retries_exhausted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "APPLY_BUMP_MAX_RETRIES", 1)
    repo = tmp_path / "repo"
    _ = repo.mkdir()
    plugin = repo / ".claude-plugin"
    _ = plugin.mkdir(parents=True)
    plugin_json = plugin / "plugin.json"
    _ = plugin_json.write_text('{"version": "1.0.0"}\n', encoding="utf-8")
    fetch_calls = 0

    class RetryRunner:
        def run(
            self,
            argv: Sequence[str],
            *,
            timeout: float | None = None,
            cwd: str | None = None,
            env: Mapping[str, str] | None = None,
            check: bool = False,
        ) -> CommandResult:
            _ = timeout, cwd, env, check
            nonlocal fetch_calls
            if len(argv) >= 3 and argv[0] == "git" and argv[1] == "status":
                return CommandResult(tuple(argv), 0, "", "", 0.01)
            if len(argv) >= 4 and tuple(argv[:4]) == ("git", "fetch", "origin", "main"):
                fetch_calls += 1
                return CommandResult(tuple(argv), 0, "", "", 0.01)
            if len(argv) >= 3 and argv[0] == "git" and argv[1] == "show" and "origin/main" in argv[2]:
                current = json.loads(plugin_json.read_text(encoding="utf-8"))["version"]
                return CommandResult(
                    tuple(argv),
                    0,
                    json.dumps({"version": current}) + "\n",
                    "",
                    0.01,
                )
            if len(argv) >= 3 and argv[0] == "git" and argv[1] == "add":
                return CommandResult(tuple(argv), 0, "", "", 0.01)
            if len(argv) >= 4 and tuple(argv[:4]) == ("git", "reset", "HEAD", config.PLUGIN_JSON_PATH):
                return CommandResult(tuple(argv), 0, "", "", 0.01)
            msg = f"unexpected: {argv}"
            raise AssertionError(msg)

    result = version_bump.apply_bump(RetryRunner(), "1.0.1", cwd=str(repo))
    assert result.applied is False
    assert "retries" in result.error.lower()
    assert fetch_calls == 2


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
            ("git", "add", config.PLUGIN_JSON_PATH): CommandResult(
                ("git", "add", config.PLUGIN_JSON_PATH), 0, "", "", 0.01
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
    result = version_bump.apply_bump(runner, "1.0.1", cwd=str(repo))
    assert result.applied is True


def _init_repo_with_origin(tmp_path: Path) -> tuple[Path, int]:
    _ = tmp_path.mkdir(parents=True, exist_ok=True)
    base = tmp_path / "origin.git"
    _ = base.mkdir(parents=True, exist_ok=True)
    _ = subprocess.run(["git", "init", "-q", "--bare", str(base)], check=True)
    repo = tmp_path / "work"
    _ = repo.mkdir()
    _ = subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    _ = subprocess.run(["git", "config", "user.email", "t@e.com"], cwd=repo, check=True)
    _ = subprocess.run(["git", "config", "user.name", "T"], cwd=repo, check=True)
    plugin = repo / ".claude-plugin"
    _ = plugin.mkdir(parents=True)
    _ = (plugin / "plugin.json").write_text('{"version":"1.0.0"}\n', encoding="utf-8")
    _ = subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    _ = subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)
    _ = subprocess.run(["git", "remote", "add", "origin", str(base)], cwd=repo, check=True)
    _ = subprocess.run(["git", "push", "-q", "origin", "main"], cwd=repo, check=True)
    pre = version_bump.check_bump_version_pre(ProcRunner(), cwd=str(repo))
    return repo, pre.commits_before


@pytest.mark.skipif(
    not APPLY_SH.is_file() or shutil.which("bash") is None,
    reason="apply-bump.sh or bash unavailable",
)
def test_parity_apply_bump_success_with_origin(tmp_path: Path) -> None:
    repo_bash, _ = _init_repo_with_origin(tmp_path / "bash")
    repo_py, _ = _init_repo_with_origin(tmp_path / "py")
    bash = subprocess.run(
        ["bash", str(APPLY_SH), "--new-version", "1.0.1"],
        cwd=repo_bash,
        capture_output=True,
        text=True,
        check=False,
    )
    py = version_bump.apply_bump(ProcRunner(), "1.0.1", cwd=str(repo_py))
    bash_kv = _parse_kv(bash.stdout)
    assert bash_kv.get("APPLIED", "").lower() == "true"
    assert py.applied is True
    assert py.commit_sha
    assert json.loads((repo_py / ".claude-plugin/plugin.json").read_text())["version"] == "1.0.1"


@pytest.mark.skipif(
    not CHECK_SH.is_file() or shutil.which("bash") is None,
    reason="check-bump-version.sh or bash unavailable",
)
def test_parity_check_bump_post(tmp_path: Path) -> None:
    repo, before = _init_repo_with_origin(tmp_path)
    plugin = repo / ".claude-plugin/plugin.json"
    _ = plugin.write_text('{"version":"1.0.1"}\n', encoding="utf-8")
    _ = subprocess.run(["git", "add", plugin], cwd=repo, check=True)
    _ = subprocess.run(["git", "commit", "-q", "-m", "Bump version to 1.0.1"], cwd=repo, check=True)
    bash = subprocess.run(
        ["bash", str(CHECK_SH), "--mode", "post", "--before-count", str(before)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    py = version_bump.verify_bump_commit_count(ProcRunner(), before, cwd=str(repo))
    bash_kv = _parse_kv(bash.stdout)
    assert str(py.verified).lower() == bash_kv.get("VERIFIED", "").lower()
    assert str(py.commits_after) == bash_kv.get("COMMITS_AFTER")
    assert py.status == bash_kv.get("STATUS")


def test_classify_deleted_skill_major(tmp_path: Path) -> None:
    repo = _init_bump_repo(tmp_path)
    skill = repo / "skills/base/SKILL.md"
    _ = subprocess.run(["git", "rm", "-q", str(skill.relative_to(repo))], cwd=repo, check=True)
    _ = subprocess.run(["git", "commit", "-q", "-m", "remove base skill"], cwd=repo, check=True)
    result = version_bump.classify_bump(ProcRunner(), cwd=str(repo))
    assert result.bump_type == "MAJOR"
    assert any("Deleted" in reason for reason in result.major_reasons)


def test_drop_reset_at_head(tmp_path: Path) -> None:
    repo = _init_bump_repo(tmp_path)
    plugin = repo / ".claude-plugin/plugin.json"
    _ = plugin.write_text('{"version":"2.0.0"}\n', encoding="utf-8")
    _ = subprocess.run(["git", "add", plugin], cwd=repo, check=True)
    _ = subprocess.run(["git", "commit", "-q", "-m", "Bump version to 2.0.0"], cwd=repo, check=True)
    result = version_bump.drop_bump_commit(ProcRunner(), cwd=str(repo))
    assert result.dropped is True
    assert json.loads(plugin.read_text(encoding="utf-8"))["version"] == "1.2.2"
