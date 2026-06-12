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
import release_finish
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


class ReleaseFinishRunner:
    def __init__(self, *, remote_tag: str = "", local_tag: str = "", release_exists: bool = True, merge_oid: str = "abc1234"):
        self.remote_tag = remote_tag
        self.local_tag = local_tag
        self.release_exists = release_exists
        self.merge_oid = merge_oid
        self.calls: list[list[str]] = []

    def run(self, argv, **_kwargs):
        self.calls.append(list(argv))
        if argv[:3] == ["git", "fetch", "origin"]:
            return cr(argv)
        if argv[:4] == ["gh", "pr", "view", "5"] and argv[-1] == "mergeCommit":
            value = {"oid": self.merge_oid} if self.merge_oid else None
            return cr(argv, json.dumps({"mergeCommit": value}))
        if argv[:4] == ["gh", "pr", "view", "5"] and argv[-1] == "state":
            return cr(argv, '{"state":"MERGED"}\n')
        if argv[:3] == ["git", "rev-parse", "--verify"]:
            target = argv[3]
            if target == "abc1234^{commit}":
                return cr(argv, "abc1234\n")
            if target == "v1.2.3^{commit}" and self.local_tag:
                return cr(argv, f"{self.local_tag}\n")
            if target == "v1.2.3^{commit}":
                return cr(argv, rc=1)
        if argv[:2] == ["git", "rev-parse"] and argv[2] == "origin/main^{commit}":
            return cr(argv, "abc1234\n")
        if argv[:2] == ["git", "rev-parse"] and argv[2] == "abc1234^{commit}":
            return cr(argv, "abc1234\n")
        if argv[:3] == ["git", "merge-base", "--is-ancestor"]:
            return cr(argv)
        if argv[:3] == ["git", "ls-remote", "origin"]:
            return cr(argv, self.remote_tag)
        if argv[:2] == ["git", "tag"]:
            return cr(argv)
        if argv[:2] == ["git", "push"]:
            return cr(argv)
        if argv[:3] == ["gh", "release", "view"]:
            return cr(argv, rc=0 if self.release_exists else 1)
        if argv[:3] == ["gh", "release", "edit"]:
            return cr(argv)
        if argv[:3] == ["gh", "release", "create"]:
            return cr(argv)
        raise AssertionError(f"unexpected argv: {argv}")


def _patch_release_finish(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, runner: ReleaseFinishRunner) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    notes = tmp_path / "notes.md"
    notes.write_text("notes\n", encoding="utf-8")
    monkeypatch.setattr(release_finish, "_repo_root", lambda: root)
    monkeypatch.setattr(release_finish, "_origin_repo", lambda _root: "o/r")
    monkeypatch.setattr(release_finish, "_plugin_version_at", lambda _oid: "1.2.3")
    def promote(version, repo, root):
        runner.calls.append(["promote", version, repo, str(root)])
        return cr(("promote", version, repo, str(root)))
    monkeypatch.setattr(release_finish, "_promote_release", promote)
    monkeypatch.setattr(release_finish.proc, "run", runner.run)
    monkeypatch.setattr(release_finish.time, "sleep", lambda _seconds: None)
    return notes


def test_release_finish_remote_lightweight_tag_skips_push_and_edits_release(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = ReleaseFinishRunner(remote_tag="abc1234\trefs/tags/v1.2.3\n", release_exists=True)
    notes = _patch_release_finish(monkeypatch, tmp_path, runner)
    assert release_finish.main(["--version","1.2.3","--notes-file",str(notes),"--repo","o/r","--pr","5"]) == 0
    out = capsys.readouterr().out
    assert "RELEASE_ACTION=edit" in out
    assert not any(call[:2] == ["git", "push"] for call in runner.calls)


def test_release_finish_existing_local_tag_creates_missing_release_and_promotes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = ReleaseFinishRunner(local_tag="abc1234", release_exists=False)
    notes = _patch_release_finish(monkeypatch, tmp_path, runner)
    assert release_finish.main(["--version","1.2.3","--notes-file",str(notes),"--repo","o/r","--pr","5"]) == 0
    out = capsys.readouterr().out
    assert "RELEASE_ACTION=create" in out
    assert any(call[:3] == ["gh", "release", "create"] for call in runner.calls)
    assert any(call[0] == "promote" for call in runner.calls)


def test_release_finish_falls_back_to_origin_main_when_merge_commit_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = ReleaseFinishRunner(local_tag="abc1234", release_exists=True, merge_oid="")
    notes = _patch_release_finish(monkeypatch, tmp_path, runner)
    assert release_finish.main(["--version","1.2.3","--notes-file",str(notes),"--repo","o/r","--pr","5"]) == 0
    assert "TARGET_OID=abc1234" in capsys.readouterr().out
    assert sum(call[:4] == ["gh", "pr", "view", "5"] and call[-1] == "mergeCommit" for call in runner.calls) == 5


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


def test_promote_latest_failure_ignores_inherited_quiet(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = QueueRunner([
        cr(["gh"], stderr="raw gh failure", rc=1),
    ])
    quiet_log = tmp_path / "quiet.log"
    monkeypatch.setenv("LARCH_QUIET_ACTIVE", "1")
    monkeypatch.setenv("LARCH_QUIET_PID", "999999")
    monkeypatch.setenv("LARCH_QUIET_LOG_FILE", str(quiet_log))
    monkeypatch.setattr(promote_release.proc, "run", runner.run)
    assert promote_release.promote_latest_main(["--repo", "o/r"]) == 1
    assert capsys.readouterr().err.startswith("ERROR=raw gh failure")
    assert not quiet_log.exists()


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
