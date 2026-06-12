# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false
# ruff: noqa: TC002
# pylint: skip-file
"""Representative tests for release Python helpers."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import promote_release
import release_prepare
import verify_main
import version_bump
from proc import CommandResult


class QueueRunner:
    def __init__(self, responses: list[CommandResult]):
        self.responses = responses
        self.calls: list[list[str]] = []

    def run(self, argv, **_kwargs):
        self.calls.append(list(argv))
        if not self.responses:
            return CommandResult(tuple(argv), 0, "", "", 0.01)
        return self.responses.pop(0)


def cr(argv, stdout="", stderr="", rc=0):
    return CommandResult(tuple(argv), rc, stdout, stderr, 0.01)


def test_read_plugin_version_best_effort(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    root = tmp_path / "plugin"
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin/plugin.json").write_text('{"version":"9.8.7"}\n', encoding="utf-8")
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(root))
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    assert version_bump.read_plugin_version_main([]) == 0
    assert capsys.readouterr().out == "LARCH_PLUGIN_VERSION=9.8.7\n"


def test_plugin_read_version_cli_captures_stdout_with_inherited_quiet(tmp_path: Path) -> None:
    root = tmp_path / "plugin"
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin/plugin.json").write_text('{"version":"9.8.7"}\n', encoding="utf-8")
    env = os.environ.copy()
    env.update({
        "CLAUDE_PLUGIN_ROOT": str(root),
        "LARCH_QUIET_ACTIVE": "1",
        "LARCH_QUIET_PID": "999999",
        "LARCH_QUIET_LOG_FILE": str(tmp_path / "quiet.log"),
    })
    res = subprocess.run([sys.executable, str(Path(__file__).with_name("cli.py")), "plugin", "read-version"], capture_output=True, text=True, env=env, check=False)
    assert res.returncode == 0
    assert res.stdout == "LARCH_PLUGIN_VERSION=9.8.7\n"


def test_set_version_rejects_downgrade(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    plugin = tmp_path / "plugin.json"
    plugin.write_text(json.dumps({"version": "2.0.0"}), encoding="utf-8")
    monkeypatch.setenv("LARCH_RELEASE_SET_VERSION_PLUGIN_JSON", str(plugin))
    assert version_bump.set_version_main(["1.9.9"]) == 1
    assert "downgrade refused" in capsys.readouterr().err


def test_promote_latest_dry_run_emits_prelude(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = QueueRunner([
        cr(["gh"], json.dumps([{"tagName":"v1.2.3","isPrerelease":True,"isLatest":False,"publishedAt":"2026-01-01T00:00:00Z"}]))
    ])
    monkeypatch.setattr(promote_release.proc, "run", runner.run)
    assert promote_release.promote_latest_main(["--repo", "o/r", "--dry-run"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert "RELEASE_TAG=v1.2.3" in out
    assert "DRY_RUN=true" in out
    assert not any(line == "DRY_RUN=false" for line in out)


def test_promote_latest_errors_are_error_kv_prefixed(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = QueueRunner([
        cr(["gh"], stderr="raw gh failure", rc=1),
    ])
    monkeypatch.setattr(promote_release.proc, "run", runner.run)
    assert promote_release.promote_latest_main(["--repo", "o/r"]) == 1
    assert capsys.readouterr().err.startswith("ERROR=raw gh failure")


def test_release_prepare_override_recomputes_from_current() -> None:
    assert release_prepare._apply_override("1.2.3", "minor") == ("MINOR", "1.3.0")


def test_verify_main_direct_title_and_suffix(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(verify_main.proc, "run", lambda argv: cr(tuple(argv), stdout="abc123 Feature title (#42)\n"))
    assert verify_main.main(["--expected-title", "Different title (#42)"]) == 0
    out = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    assert out["VERIFIED"] == "true"
    assert out["COMMIT_HASH"] == "abc123"


def test_verify_main_direct_mismatch(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(verify_main.proc, "run", lambda argv: cr(tuple(argv), stdout="abc123 Other title\n"))
    assert verify_main.main(["--expected-title", "Feature title (#42)"]) == 0
    out = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    assert out["VERIFIED"] == "false"


class ReleasePrepareRunner:
    def __init__(self, repo_root: Path, *, log_subjects: str = "Feature (#12)\n", log_hash_subjects: str = "abc Feature (#12)\n", api_stdout: str = "[]\n", api_rc: int = 0):
        self.repo_root = repo_root
        self.calls: list[tuple[list[str], str | None]] = []
        self.log_subjects = log_subjects
        self.log_hash_subjects = log_hash_subjects
        self.api_stdout = api_stdout
        self.api_rc = api_rc

    def run(self, argv, **kwargs):
        cwd = kwargs.get("cwd")
        self.calls.append((list(argv), cwd))
        if argv[0] == "git":
            assert cwd == str(self.repo_root)
            if argv[:2] == ["git", "fetch"]:
                return cr(tuple(argv))
            if argv[:2] == ["git", "rev-parse"]:
                return cr(tuple(argv), stdout="same-sha\n")
            if argv[:2] == ["git", "merge-base"]:
                return cr(tuple(argv))
            if argv[:2] == ["git", "show"]:
                return cr(tuple(argv), stdout='{"version":"1.2.3"}\n')
            if argv[:2] == ["git", "log"] and "--format=%H %s" in argv:
                return cr(tuple(argv), stdout=self.log_hash_subjects)
            if argv[:2] == ["git", "log"]:
                return cr(tuple(argv), stdout=self.log_subjects)
        if argv[:2] == ["gh", "api"]:
            return cr(tuple(argv), stdout=self.api_stdout, rc=self.api_rc)
        return cr(tuple(argv))


class Classification:
    current_version = "1.2.3"
    new_version = "1.2.4"
    bump_type = "PATCH"


def _prepare_common(monkeypatch: pytest.MonkeyPatch, runner: ReleasePrepareRunner, *, repo: str = "o/r", pr_view: object | None = None) -> None:
    monkeypatch.setattr(release_prepare.proc, "run", runner.run)
    monkeypatch.setattr(release_prepare, "_origin_repo", lambda _root: repo)
    def gh_json(argv):
        if argv[:2] == ["release", "list"]:
            return [{"tagName": "v1.2.3", "isLatest": True}]
        if argv[:2] == ["pr", "list"]:
            return []
        if argv[:2] == ["pr", "view"]:
            return pr_view
        raise AssertionError(f"unexpected gh json argv: {argv}")
    monkeypatch.setattr(release_prepare, "_gh_json", gh_json)
    monkeypatch.setattr(release_prepare.version_bump, "classify_bump", lambda *_args, **_kwargs: Classification())


def test_release_prepare_git_commands_run_in_repo_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = Path(release_prepare.__file__).resolve().parents[1]
    runner = ReleasePrepareRunner(repo_root)
    _prepare_common(monkeypatch, runner, pr_view={"number": 12, "title": "Feature", "labels": [], "author": {"login": "me"}, "url": "u"})
    assert release_prepare.main(["--repo", "o/r", "--out-dir", str(tmp_path)]) == 0
    assert any(call[0][:2] == ["git", "log"] and call[1] == str(repo_root) for call in runner.calls)


def test_release_prepare_origin_repo_mismatch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(release_prepare, "_origin_repo", lambda _root: "other/repo")
    assert release_prepare.main(["--repo", "o/r", "--out-dir", str(tmp_path)]) == 1
    assert "ERROR=origin-repo-mismatch" in capsys.readouterr().out


def test_release_prepare_pr_metadata_incomplete(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo_root = Path(release_prepare.__file__).resolve().parents[1]
    runner = ReleasePrepareRunner(repo_root)
    _prepare_common(monkeypatch, runner, pr_view=None)
    assert release_prepare.main(["--repo", "o/r", "--out-dir", str(tmp_path)]) == 1
    assert "ERROR=pr-metadata-incomplete" in capsys.readouterr().out


def test_release_prepare_commit_to_pulls_note(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo_root = Path(release_prepare.__file__).resolve().parents[1]
    pulls = json.dumps([{"number": 13, "title": "Orphan PR", "labels": [], "user": {"login": "me"}, "html_url": "u"}])
    runner = ReleasePrepareRunner(repo_root, log_subjects="", log_hash_subjects="def Orphan subject\n", api_stdout=pulls)
    _prepare_common(monkeypatch, runner)
    assert release_prepare.main(["--repo", "o/r", "--out-dir", str(tmp_path)]) == 0
    assert "NOTE: commit def resolved to PR #13" in capsys.readouterr().err


def test_release_prepare_unmatched_commit_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo_root = Path(release_prepare.__file__).resolve().parents[1]
    runner = ReleasePrepareRunner(repo_root, log_subjects="", log_hash_subjects="def Orphan subject\n", api_stdout="[]\n")
    _prepare_common(monkeypatch, runner)
    assert release_prepare.main(["--repo", "o/r", "--out-dir", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "UNMATCHED_COMMITS=def" in out
    assert "ERROR=unmatched-commits" in out
