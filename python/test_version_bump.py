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
from errors import ShipError, Stalled
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
    result = version_bump.apply_bump(runner, "1.0.1")
    assert "/Users/secret" not in result.error


def test_bump_branch_guard_matrix() -> None:
    version_bump.bump_branch_guard("feat", "feat", forked=False)
    with pytest.raises(Stalled):
        version_bump.bump_branch_guard("", "feat", forked=False)
    with pytest.raises(Stalled):
        version_bump.bump_branch_guard("feat", "other", forked=False)
    with pytest.raises(Stalled):
        version_bump.bump_branch_guard("main", "main", forked=False)
    with pytest.raises(Stalled):
        version_bump.bump_branch_guard("master", "master", forked=False)
    version_bump.bump_branch_guard("main", "main", forked=True)
    version_bump.bump_branch_guard("master", "master", forked=True)


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
        ("git", "merge-base", "main", "HEAD"): CommandResult(
            ("git", "merge-base", "main", "HEAD"), 0, f"{merge_base}\n", "", 0.01
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


def test_classify_idempotency_transparent_path_guard_refuses(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    plugin = repo / ".claude-plugin"
    _ = plugin.mkdir(parents=True)
    _ = (plugin / "plugin.json").write_text('{"version":"1.0.0"}\n', encoding="utf-8")
    runner = _classify_stub(
        head_subject="Feature",
        transparent_chain=[
            (
                f"{config.TRANSPARENT_CHANGELOG_SUBJECT_PREFIX}1.0.0",
                ["README.md"],
            ),
        ],
        name_status="",
    )
    result = version_bump.classify_bump(runner, cwd=str(repo))
    assert result.bump_type == "PATCH"


def test_classify_idempotency_depth_cap_at_three(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    plugin = repo / ".claude-plugin"
    _ = plugin.mkdir(parents=True)
    _ = (plugin / "plugin.json").write_text('{"version":"1.0.0"}\n', encoding="utf-8")
    chain = [
        (
            f"{config.TRANSPARENT_CHANGELOG_SUBJECT_PREFIX}1.0.{i}",
            [config.CHANGELOG_DEFAULT_PATH],
        )
        for i in range(3)
    ]
    runner = _classify_stub(
        head_subject="Bump version to 9.9.9",
        transparent_chain=chain,
    )
    result = version_bump.classify_bump(runner, cwd=str(repo))
    assert result.bump_type == "NONE"


def test_classify_bump_at_idem_ref_none(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    plugin = repo / ".claude-plugin"
    _ = plugin.mkdir(parents=True)
    _ = (plugin / "plugin.json").write_text('{"version":"1.2.3"}\n', encoding="utf-8")
    runner = _classify_stub(
        head_subject="Bump version to 1.2.3",
        transparent_chain=[
            (
                f"{config.TRANSPARENT_CHANGELOG_SUBJECT_PREFIX}1.2.3",
                [config.CHANGELOG_DEFAULT_PATH],
            ),
        ],
    )
    result = version_bump.classify_bump(runner, cwd=str(repo))
    assert result.bump_type == "NONE"


def test_classify_changelog_subject_spoof_skills_minor(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    plugin = repo / ".claude-plugin"
    _ = plugin.mkdir(parents=True)
    _ = (plugin / "plugin.json").write_text('{"version":"1.0.0"}\n', encoding="utf-8")
    runner = _classify_stub(
        head_subject=f"{config.TRANSPARENT_CHANGELOG_SUBJECT_PREFIX}1.2.3",
        name_status="A\tskills/new-skill/SKILL.md\n",
    )
    runner.responses[
        ("git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD")
    ] = CommandResult(
        ("git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"),
        0,
        "skills/new-skill/SKILL.md\n",
        "",
        0.01,
    )
    result = version_bump.classify_bump(runner, cwd=str(repo))
    assert result.bump_type == "MINOR"


def test_classify_added_skill_minor(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    plugin = repo / ".claude-plugin"
    _ = plugin.mkdir(parents=True)
    _ = (plugin / "plugin.json").write_text('{"version":"1.0.0"}\n', encoding="utf-8")
    runner = _classify_stub(name_status="A\tskills/new/SKILL.md\n")
    result = version_bump.classify_bump(runner, cwd=str(repo))
    assert result.bump_type == "MINOR"


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
            ("git", "merge-base", "main", "HEAD"): CommandResult(
                ("git", "merge-base", "main", "HEAD"), 0, "base\n", "", 0.01
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


def test_drop_rebase_onto_when_bump_below_head(tmp_path: Path) -> None:
    repo = _init_bump_repo(tmp_path)
    _ = (repo / "README.md").write_text("feature\n", encoding="utf-8")
    _ = subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    _ = subprocess.run(["git", "commit", "-q", "-m", "feature"], cwd=repo, check=True)
    plugin = repo / ".claude-plugin/plugin.json"
    _ = plugin.write_text('{"version":"2.0.0"}\n', encoding="utf-8")
    _ = subprocess.run(["git", "add", plugin], cwd=repo, check=True)
    _ = subprocess.run(["git", "commit", "-q", "-m", "Bump version to 2.0.0"], cwd=repo, check=True)
    result = version_bump.drop_bump_commit(ProcRunner(), cwd=str(repo))
    assert result.dropped is True
    assert json.loads(plugin.read_text(encoding="utf-8"))["version"] == "1.2.2"
    log = subprocess.run(
        ["git", "log", "--oneline", "-3"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Bump version to 2.0.0" not in log.stdout


def test_drop_bump_extra_file_refuses_drop(tmp_path: Path) -> None:
    repo = _init_bump_repo(tmp_path)
    plugin = repo / ".claude-plugin/plugin.json"
    _ = plugin.write_text('{"version":"2.0.0"}\n', encoding="utf-8")
    _ = (repo / "README.md").write_text("extra\n", encoding="utf-8")
    _ = subprocess.run(["git", "add", plugin, "README.md"], cwd=repo, check=True)
    _ = subprocess.run(["git", "commit", "-q", "-m", "Bump version to 2.0.0"], cwd=repo, check=True)
    result = version_bump.drop_bump_commit(ProcRunner(), cwd=str(repo))
    assert result.dropped is False
    assert "unexpected" in result.error.lower()


def test_drop_allow_changelog_only(tmp_path: Path) -> None:
    repo = _init_bump_repo(tmp_path)
    changelog_md = repo / "CHANGELOG.md"
    _ = changelog_md.write_text(
        changelog_md.read_text(encoding="utf-8") + "\n## [1.2.3] - 2026-01-01\n",
        encoding="utf-8",
    )
    _ = subprocess.run(["git", "add", "CHANGELOG.md"], cwd=repo, check=True)
    _ = subprocess.run(
        ["git", "commit", "-q", "-m", "Bump version to 1.2.3"],
        cwd=repo,
        check=True,
    )
    result = version_bump.drop_bump_commit(
        ProcRunner(),
        allow_changelog_only=True,
        cwd=str(repo),
    )
    assert result.dropped is True


def test_sorted_changed_files_c_locale_order(tmp_path: Path) -> None:
    from bump_worktree import sorted_changed_files

    repo = _init_bump_repo(tmp_path)
    _ = subprocess.run(
        ["git", "commit", "-q", "--allow-empty", "-m", "empty"],
        cwd=repo,
        check=True,
    )
    files = "äfile\nbfile\n"
    ordered = sorted(files.strip().split("\n"), key=lambda s: s.encode())
    runner = StubRunner(
        {
            ("git", "diff", "--name-only", "HEAD~1", "HEAD"): CommandResult(
                ("git", "diff", "--name-only", "HEAD~1", "HEAD"),
                0,
                files,
                "",
                0.01,
            ),
        },
    )
    assert sorted_changed_files(runner, "HEAD~1", "HEAD", cwd=str(repo)) == "\n".join(ordered)


@pytest.mark.skipif(
    not CLASSIFY_SH.is_file() or shutil.which("bash") is None,
    reason="classify-bump.sh or bash unavailable",
)
@pytest.mark.parametrize(
    "case",
    [
        "test1",
        "test2",
        "test3",
        "test4",
        "test5",
    ],
)
def test_parity_classify_idempotency_cases(tmp_path: Path, case: str) -> None:
    harness = REPO_ROOT / ".claude/skills/bump-version/scripts/test-classify-bump.sh"
    if not harness.is_file():
        pytest.skip("test-classify-bump.sh unavailable")
    repo = _init_bump_repo(tmp_path / case)
    if case == "test1":
        plugin = repo / ".claude-plugin/plugin.json"
        _ = plugin.write_text('{"version":"1.2.3"}\n', encoding="utf-8")
        _ = subprocess.run(["git", "add", plugin], cwd=repo, check=True)
        _ = subprocess.run(["git", "commit", "-q", "-m", "Bump version to 1.2.3"], cwd=repo, check=True)
    elif case == "test2":
        plugin = repo / ".claude-plugin/plugin.json"
        _ = plugin.write_text('{"version":"1.2.3"}\n', encoding="utf-8")
        _ = subprocess.run(["git", "add", plugin], cwd=repo, check=True)
        _ = subprocess.run(["git", "commit", "-q", "-m", "Bump version to 1.2.3"], cwd=repo, check=True)
        with (repo / "CHANGELOG.md").open("a", encoding="utf-8") as fh:
            fh.write("\n- New fix.\n")
        _ = subprocess.run(["git", "add", "CHANGELOG.md"], cwd=repo, check=True)
        _ = subprocess.run(
            ["git", "commit", "-q", "-m", "Update CHANGELOG for 1.2.3"],
            cwd=repo,
            check=True,
        )
    elif case == "test3":
        plugin = repo / ".claude-plugin/plugin.json"
        _ = plugin.write_text('{"version":"1.2.3"}\n', encoding="utf-8")
        _ = subprocess.run(["git", "add", plugin], cwd=repo, check=True)
        _ = subprocess.run(["git", "commit", "-q", "-m", "Bump version to 1.2.3"], cwd=repo, check=True)
        with (repo / "CHANGELOG.md").open("a", encoding="utf-8") as fh:
            fh.write("\n- New fix.\n")
        _ = subprocess.run(["git", "add", "CHANGELOG.md"], cwd=repo, check=True)
        _ = subprocess.run(
            ["git", "commit", "-q", "-m", "Update CHANGELOG for 1.2.3"],
            cwd=repo,
            check=True,
        )
        log_dir = repo / "larch-logs/implement/run-1"
        _ = log_dir.mkdir(parents=True)
        _ = (log_dir / "manifest.json").write_text("{}\n", encoding="utf-8")
        _ = subprocess.run(["git", "add", log_dir], cwd=repo, check=True)
        _ = subprocess.run(
            ["git", "commit", "-q", "-m", "chore(larch-logs): flush implement run run-1"],
            cwd=repo,
            check=True,
        )
    elif case == "test4":
        _ = (repo / "README.md").write_text("feature\n", encoding="utf-8")
        _ = subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
        _ = subprocess.run(["git", "commit", "-q", "-m", "Feature work"], cwd=repo, check=True)
        with (repo / "CHANGELOG.md").open("a", encoding="utf-8") as fh:
            fh.write("\n- Feature note.\n")
        _ = subprocess.run(["git", "add", "CHANGELOG.md"], cwd=repo, check=True)
        _ = subprocess.run(
            ["git", "commit", "-q", "-m", "Update CHANGELOG for 1.2.3"],
            cwd=repo,
            check=True,
        )
    elif case == "test5":
        skill = repo / "skills/new-skill/SKILL.md"
        _ = skill.parent.mkdir(parents=True)
        _ = skill.write_text("---\nname: new-skill\n---\n", encoding="utf-8")
        _ = subprocess.run(["git", "add", skill], cwd=repo, check=True)
        _ = subprocess.run(
            ["git", "commit", "-q", "-m", "Update CHANGELOG for 1.2.3"],
            cwd=repo,
            check=True,
        )
    expected_bump = {
        "test1": "NONE",
        "test2": "NONE",
        "test3": "NONE",
        "test4": "PATCH",
        "test5": None,
    }
    bash = subprocess.run(
        ["bash", str(CLASSIFY_SH)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    py = version_bump.classify_bump(ProcRunner(), cwd=str(repo))
    bash_kv = _parse_kv(bash.stdout)
    assert py.bump_type == bash_kv.get("BUMP_TYPE")
    if expected_bump[case] is not None:
        assert py.bump_type == expected_bump[case]


@pytest.mark.skipif(
    not DROP_SH.is_file() or shutil.which("bash") is None,
    reason="drop-bump-commit.sh or bash unavailable",
)
def test_parity_drop_bump_allow_changelog_only(tmp_path: Path) -> None:
    def _changelog_only_bump(repo: Path) -> None:
        changelog_md = repo / "CHANGELOG.md"
        _ = changelog_md.write_text(
            changelog_md.read_text(encoding="utf-8") + "\n## [1.2.3] - 2026-01-01\n",
            encoding="utf-8",
        )
        _ = subprocess.run(["git", "add", "CHANGELOG.md"], cwd=repo, check=True)
        _ = subprocess.run(
            ["git", "commit", "-q", "-m", "Bump version to 1.2.3"],
            cwd=repo,
            check=True,
        )

    repo_bash = _init_bump_repo(tmp_path / "bash")
    repo_py = _init_bump_repo(tmp_path / "py")
    _changelog_only_bump(repo_bash)
    _changelog_only_bump(repo_py)
    bash = subprocess.run(
        ["bash", str(DROP_SH), "--allow-changelog-only"],
        cwd=repo_bash,
        capture_output=True,
        text=True,
        check=False,
    )
    py = version_bump.drop_bump_commit(
        ProcRunner(),
        allow_changelog_only=True,
        cwd=str(repo_py),
    )
    bash_kv = _parse_kv(bash.stdout)
    assert str(py.dropped).lower() == bash_kv.get("DROPPED", "").lower()


@pytest.mark.skipif(
    not DROP_SH.is_file() or shutil.which("bash") is None,
    reason="drop-bump-commit.sh or bash unavailable",
)
def test_parity_drop_bump_success_plugin_only(tmp_path: Path) -> None:
    def _seed_bump(repo: Path) -> None:
        plugin = repo / ".claude-plugin/plugin.json"
        _ = plugin.write_text('{"version":"2.0.0"}\n', encoding="utf-8")
        _ = subprocess.run(["git", "add", plugin], cwd=repo, check=True)
        _ = subprocess.run(
            ["git", "commit", "-q", "-m", "Bump version to 2.0.0"],
            cwd=repo,
            check=True,
        )

    repo_bash = _init_bump_repo(tmp_path / "bash")
    repo_py = _init_bump_repo(tmp_path / "py")
    _seed_bump(repo_bash)
    _seed_bump(repo_py)
    bash = subprocess.run(
        ["bash", str(DROP_SH)],
        cwd=repo_bash,
        capture_output=True,
        text=True,
        check=False,
    )
    py = version_bump.drop_bump_commit(ProcRunner(), cwd=str(repo_py))
    bash_kv = _parse_kv(bash.stdout)
    assert bash_kv.get("DROPPED", "").lower() == "true"
    assert str(py.dropped).lower() == bash_kv.get("DROPPED", "").lower()
    assert json.loads((repo_py / ".claude-plugin/plugin.json").read_text())["version"] == "1.2.2"
    assert json.loads((repo_bash / ".claude-plugin/plugin.json").read_text())["version"] == "1.2.2"


def test_drop_replay_abort_failure_reports_stuck_rebase() -> None:
    from bump_worktree import drop_replay_commit

    runner = StubRunner(
        {
            ("git", "rebase", "--onto", "HEAD~2", "HEAD~1"): CommandResult(
                ("git", "rebase", "--onto", "HEAD~2", "HEAD~1"), 1, "", "conflict", 0.01
            ),
            ("git", "rebase", "--abort"): CommandResult(
                ("git", "rebase", "--abort"), 1, "", "fatal", 0.01
            ),
        },
    )
    err = drop_replay_commit(runner, found_at=1)
    assert err is not None
    assert "stuck mid-rebase" in err
