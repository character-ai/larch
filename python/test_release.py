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

from larch.release import promote_release
from larch.release import release_finish
from larch.release import release_prepare
from larch.core import verify_main
from larch.release import version_bump
from larch.core.proc import CommandResult


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
    def __init__(self, *, remote_tag: str = "", local_tag: str = "", release_exists: bool = True, merge_oid: str = "abc1234", unresolved_target_attempts: int = 0, ancestry_failures: int = 0):
        self.remote_tag = remote_tag
        self.local_tag = local_tag
        self.release_exists = release_exists
        self.merge_oid = merge_oid
        self.unresolved_target_attempts = unresolved_target_attempts
        self.ancestry_failures = ancestry_failures
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
                if self.unresolved_target_attempts > 0:
                    self.unresolved_target_attempts -= 1
                    return cr(argv, rc=1)
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
            if self.ancestry_failures > 0:
                self.ancestry_failures -= 1
                return cr(argv, rc=1)
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


def test_release_finish_retries_until_target_reaches_origin_main(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = ReleaseFinishRunner(local_tag="abc1234", unresolved_target_attempts=2, ancestry_failures=1)
    notes = _patch_release_finish(monkeypatch, tmp_path, runner)
    assert release_finish.main(["--version","1.2.3","--notes-file",str(notes),"--repo","o/r","--pr","5"]) == 0
    assert "TARGET_OID=abc1234" in capsys.readouterr().out
    assert sum(call[:3] == ["git", "fetch", "origin"] for call in runner.calls) > 2


def test_release_finish_origin_repo_mismatch_blocks_side_effects(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    notes = tmp_path / "notes.md"
    notes.write_text("notes\n", encoding="utf-8")
    runner = ReleaseFinishRunner()
    monkeypatch.setattr(release_finish, "_repo_root", lambda: root)
    monkeypatch.setattr(release_finish, "_origin_repo", lambda _root: "other/repo")
    monkeypatch.setattr(release_finish.proc, "run", runner.run)
    assert release_finish.main(["--version","1.2.3","--notes-file",str(notes),"--repo","o/r","--pr","5"]) == 1
    assert "ERROR=origin-repo-mismatch" in capsys.readouterr().err
    assert runner.calls == []


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


def test_promote_validation_errors_exit_one(capsys: pytest.CaptureFixture[str]) -> None:
    assert promote_release.promote_main(["1.2", "--repo", "o/r"]) == 1
    assert "ERROR=invalid semver format" in capsys.readouterr().err
    assert promote_release.promote_main(["1.2.3", "--repo", "not-a-repo"]) == 1
    assert "ERROR=invalid --repo value" in capsys.readouterr().err


def test_promote_checks_prerelease_probe_return_code_when_already_latest(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = QueueRunner([
        cr(["gh"]),
        cr(["gh"], "v1.2.3\n"),
        cr(["gh"], stderr="auth failed", rc=1),
    ])
    monkeypatch.setattr(promote_release.proc, "run", runner.run)
    assert promote_release.promote_main(["1.2.3", "--repo", "o/r"]) == 1
    assert capsys.readouterr().err.startswith("ERROR=auth failed")


def test_promote_latest_preserves_empty_boolean_fields(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = QueueRunner([
        cr(["gh"], json.dumps([{"tagName":"v1.2.3","publishedAt":"2026-01-01T00:00:00Z"}])),
        cr(["gh"]),
        cr(["gh"], json.dumps([{"tagName":"v1.2.3","isPrerelease":False,"isLatest":True}])),
    ])
    monkeypatch.setattr(promote_release.proc, "run", runner.run)
    assert promote_release.promote_latest_main(["--repo", "o/r"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert "RELEASE_WAS_PRERELEASE=" in out
    assert "RELEASE_WAS_LATEST=" in out
    assert "RELEASE_ALREADY_LATEST=false" in out
    assert any(call[:3] == ["gh", "release", "edit"] for call in runner.calls)


def test_promote_latest_verification_failure_keeps_phase_kvs(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = QueueRunner([
        cr(["gh"], json.dumps([{"tagName":"v1.2.3","isPrerelease":True,"isLatest":False,"publishedAt":"2026-01-01T00:00:00Z"}])),
        cr(["gh"]),
        cr(["gh"], json.dumps([{"tagName":"v1.2.3","isPrerelease":True,"isLatest":False}])),
    ])
    monkeypatch.setattr(promote_release.proc, "run", runner.run)
    assert promote_release.promote_latest_main(["--repo", "o/r"]) == 1
    captured = capsys.readouterr()
    out = captured.out.splitlines()
    assert "RELEASE_ALREADY_LATEST=false" in out
    assert "RELEASE_IS_PRERELEASE=true" in out
    assert "RELEASE_IS_LATEST=false" in out
    assert captured.err.startswith("ERROR=Release v1.2.3 verification failed")


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
    assert release_prepare._apply_override(current="1.2.3", override="minor") == ("MINOR", "1.3.0")


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


def test_verify_main_unnumbered_expected_prefix(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(verify_main.proc, "run", lambda argv: cr(tuple(argv), stdout="abc123 Feature follow-up\n"))
    assert verify_main.main(["--expected-title", "Feature"]) == 0
    out = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    assert out["VERIFIED"] == "true"


def test_verify_main_numbered_expected_exact(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(verify_main.proc, "run", lambda argv: cr(tuple(argv), stdout="abc123 Title (#7)\n"))
    assert verify_main.main(["--expected-title", "Title (#7)"]) == 0
    out = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    assert out["VERIFIED"] == "true"


def test_verify_main_numbered_expected_suffix_only(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(verify_main.proc, "run", lambda argv: cr(tuple(argv), stdout="abc123 Feature title (#42)\n"))
    assert verify_main.main(["--expected-title", "Different title (#42)"]) == 0
    out = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    assert out["VERIFIED"] == "true"


def test_verify_main_rejects_mid_string_suffix(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(verify_main.proc, "run", lambda argv: cr(tuple(argv), stdout="abc123 (#42) Feature title\n"))
    assert verify_main.main(["--expected-title", "Different title (#42)"]) == 0
    out = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    assert out["VERIFIED"] == "false"


def test_verify_main_rejects_numbered_expected_stripped_prefix(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(verify_main.proc, "run", lambda argv: cr(tuple(argv), stdout="abc123 Title follow-up\n"))
    assert verify_main.main(["--expected-title", "Title (#7)"]) == 0
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
    repo_root = Path(release_prepare.__file__).resolve().parents[3]
    runner = ReleasePrepareRunner(repo_root)
    _prepare_common(monkeypatch, runner, pr_view={"number": 12, "title": "Feature", "labels": [], "author": {"login": "me"}, "url": "u"})
    assert release_prepare.main(["--repo", "o/r", "--out-dir", str(tmp_path)]) == 0
    assert any(call[0][:2] == ["git", "log"] and call[1] == str(repo_root) for call in runner.calls)


def test_release_prepare_origin_repo_mismatch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(release_prepare, "_origin_repo", lambda _root: "other/repo")
    assert release_prepare.main(["--repo", "o/r", "--out-dir", str(tmp_path)]) == 1
    assert "ERROR=origin-repo-mismatch" in capsys.readouterr().out


def test_release_prepare_pr_metadata_incomplete(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo_root = Path(release_prepare.__file__).resolve().parents[3]
    runner = ReleasePrepareRunner(repo_root)
    _prepare_common(monkeypatch, runner, pr_view=None)
    assert release_prepare.main(["--repo", "o/r", "--out-dir", str(tmp_path)]) == 1
    assert "ERROR=pr-metadata-incomplete" in capsys.readouterr().out


def test_release_prepare_commit_to_pulls_note(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo_root = Path(release_prepare.__file__).resolve().parents[3]
    pulls = json.dumps([{"number": 13, "title": "Orphan PR", "labels": [], "user": {"login": "me"}, "html_url": "u"}])
    runner = ReleasePrepareRunner(repo_root, log_subjects="", log_hash_subjects="def Orphan subject\n", api_stdout=pulls)
    _prepare_common(monkeypatch, runner)
    assert release_prepare.main(["--repo", "o/r", "--out-dir", str(tmp_path)]) == 0
    assert "NOTE: commit def resolved to PR #13" in capsys.readouterr().err


def test_release_prepare_unmatched_commit_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo_root = Path(release_prepare.__file__).resolve().parents[3]
    runner = ReleasePrepareRunner(repo_root, log_subjects="", log_hash_subjects="def Orphan subject\n", api_stdout="[]\n")
    _prepare_common(monkeypatch, runner)
    assert release_prepare.main(["--repo", "o/r", "--out-dir", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "UNMATCHED_COMMITS=def" in out
    assert "ERROR=unmatched-commits" in out


def test_release_prepare_no_unique_latest_emits_latest_count(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(release_prepare, "_origin_repo", lambda _root: "o/r")
    monkeypatch.setattr(release_prepare, "_gh_json", lambda _argv: [{"tagName": "v1.2.3", "isLatest": True}, {"tagName": "v1.2.4", "isLatest": True}])
    assert release_prepare.main(["--repo", "o/r", "--out-dir", str(tmp_path)]) == 1
    out = capsys.readouterr().out.splitlines()
    assert out == ["ERROR=no-unique-latest-release", "LATEST_COUNT=2"]


def test_release_prepare_pr_list_tsv_column_order(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = Path(release_prepare.__file__).resolve().parents[3]
    runner = ReleasePrepareRunner(repo_root)
    pr_view = {
        "number": 12,
        "title": "Feature title",
        "labels": [{"name": "enhancement"}, {"name": "release-note"}],
        "author": {"login": "alice"},
        "url": "https://github.com/o/r/pull/12",
    }
    _prepare_common(monkeypatch, runner, pr_view=pr_view)
    assert release_prepare.main(["--repo", "o/r", "--out-dir", str(tmp_path)]) == 0
    assert (tmp_path / "pr-list.tsv").read_text(encoding="utf-8").splitlines() == [
        "12\tFeature title\tenhancement,release-note\talice\thttps://github.com/o/r/pull/12"
    ]


def test_release_prepare_ignores_larch_logs_prs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo_root = Path(release_prepare.__file__).resolve().parents[3]
    runner = ReleasePrepareRunner(
        repo_root,
        log_subjects="Feature (#12)\nchore(larch-logs): flush abc (#13)\nchore(larch-logs): design run def (#14)\n",
        log_hash_subjects="h1 Feature (#12)\nh2 chore(larch-logs): flush abc (#13)\nh3 chore(larch-logs): design run def (#14)\n",
    )
    pr_views = {
        12: {"number": 12, "title": "Feature", "labels": [], "author": {"login": "alice"}, "url": "u12"},
        13: {"number": 13, "title": "chore(larch-logs): flush abc", "labels": [], "author": {"login": "bot"}, "url": "u13"},
        14: {"number": 14, "title": "chore(larch-logs): design run def", "labels": [], "author": {"login": "bot"}, "url": "u14"},
    }
    monkeypatch.setattr(release_prepare.proc, "run", runner.run)
    monkeypatch.setattr(release_prepare, "_origin_repo", lambda _root: "o/r")
    def gh_json(argv: list[str]) -> object:
        if argv[:2] == ["release", "list"]:
            return [{"tagName": "v1.2.3", "isLatest": True}]
        if argv[:2] == ["pr", "list"]:
            return []
        if argv[:2] == ["pr", "view"]:
            return pr_views[int(argv[2])]
        raise AssertionError(f"unexpected gh json argv: {argv}")
    monkeypatch.setattr(release_prepare, "_gh_json", gh_json)
    monkeypatch.setattr(release_prepare.version_bump, "classify_bump", lambda *_args, **_kwargs: Classification())
    assert release_prepare.main(["--repo", "o/r", "--out-dir", str(tmp_path)]) == 0
    out = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    assert out["PR_COUNT"] == "1"
    assert out["IGNORED_LARCHLOG_PR_COUNT"] == "2"
    assert (tmp_path / "pr-list.tsv").read_text(encoding="utf-8").splitlines() == ["12\tFeature\t\talice\tu12"]


def test_release_prepare_ignores_larch_logs_pr_via_commit_to_pulls(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo_root = Path(release_prepare.__file__).resolve().parents[3]
    pulls = json.dumps([{"number": 13, "title": "chore(larch-logs): flush abc", "labels": [], "user": {"login": "bot"}, "html_url": "u13"}])
    runner = ReleasePrepareRunner(repo_root, log_subjects="", log_hash_subjects="h2 chore(larch-logs): flush abc\n", api_stdout=pulls)
    _prepare_common(monkeypatch, runner)
    assert release_prepare.main(["--repo", "o/r", "--out-dir", str(tmp_path)]) == 0
    out = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    assert out["PR_COUNT"] == "0"
    assert out["IGNORED_LARCHLOG_PR_COUNT"] == "1"
    assert (tmp_path / "pr-list.tsv").read_text(encoding="utf-8") == ""
