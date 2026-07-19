# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false
# pylint: skip-file
"""Representative tests for release Python helpers."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from larch.release import promote_release
from larch.release import release_finish
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


class ReleaseStateRunner:
    def __init__(self, *, ancestry_ok: bool = True):
        self.ancestry_ok = ancestry_ok
        self.calls: list[list[str]] = []

    def run(self, argv, **_kwargs):
        self.calls.append(list(argv))
        if argv[:3] == ["git", "merge-base", "--is-ancestor"]:
            return cr(argv, rc=0 if self.ancestry_ok else 1)
        return cr(argv)


SOURCE_COMMIT = "a" * 40


def _candidate(tmp_path: Path) -> release_finish.ReleaseCandidate:
    return release_finish.ReleaseCandidate("1.2.3", "o/r", 5, SOURCE_COMMIT, tmp_path)


def _release_state(
    *, draft: bool, immutable: bool, names: tuple[str, ...] = ()
) -> release_finish.ReleaseState:
    remote_assets = tuple(
        release_finish.RemoteAsset(
            name=name, size=1, digest="sha256:" + "0" * 64, state="uploaded"
        )
        for name in names
    )
    return release_finish.ReleaseState(7, "v1.2.3", draft, immutable, remote_assets)


def test_release_ensure_policy_mutates_then_reverifies(tmp_path: Path) -> None:
    runner = QueueRunner(
        [
            cr(["gh"]),  # lint-gh-argv-literal: ok fixture assertion
            cr(["gh"]),  # lint-gh-argv-literal: ok fixture assertion
            cr(["gh"], '{"allow_merge_commit":true}'),  # lint-gh-argv-literal: ok fixture assertion
            cr(["gh"], '{"enabled":true,"enforced_by_owner":false}'),  # lint-gh-argv-literal: ok fixture assertion
        ]
    )
    release_finish.ensure_policy(runner=runner, repo="o/r", cwd=tmp_path)
    assert [call[2] for call in runner.calls[:2]] == ["--method", "--method"]
    assert runner.calls[2][:3] == ["gh", "api", "repos/o/r"]  # lint-gh-argv-literal: ok fixture assertion
    assert runner.calls[3][-1] == "repos/o/r/immutable-releases"


def test_release_list_probe_handles_missing_and_access_failure(tmp_path: Path) -> None:
    missing_runner = QueueRunner([cr(["gh"], "[]")])  # lint-gh-argv-literal: ok fixture assertion
    assert (
        release_finish._release_state(
            missing_runner,
            repo="o/r",
            tag="v1.2.3",
            cwd=tmp_path,
            missing_ok=True,
        )
        is None
    )

    denied_runner = QueueRunner(
        [cr(["gh"], stderr="gh: Resource not accessible (HTTP 403)\n", rc=1)]  # lint-gh-argv-literal: ok fixture assertion
    )
    with pytest.raises(release_finish.ReleaseError, match="release list read failed"):
        _ = release_finish._release_state(
            denied_runner,
            repo="o/r",
            tag="v1.2.3",
            cwd=tmp_path,
            missing_ok=True,
        )


def test_release_list_rejects_duplicate_drafts_for_same_tag(tmp_path: Path) -> None:
    draft = {
        "id": 7,
        "tag_name": "v1.2.3",
        "draft": True,
        "immutable": False,
        "assets": [],
    }
    runner = QueueRunner(
        [cr(["gh"], json.dumps([draft, {**draft, "id": 8}]))]  # lint-gh-argv-literal: ok fixture assertion
    )

    with pytest.raises(release_finish.ReleaseError, match="multiple releases found"):
        _ = release_finish._release_state(
            runner,
            repo="o/r",
            tag="v1.2.3",
            cwd=tmp_path,
            missing_ok=True,
        )


def test_release_stage_resume_reuses_same_draft(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        release_finish, "_verify_policy", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        release_finish,
        "_pr_state",
        lambda *_args, **_kwargs: release_finish.PullRequestState(
            "OPEN", SOURCE_COMMIT
        ),
    )
    monkeypatch.setattr(
        release_finish, "_plugin_version_at", lambda *_args, **_kwargs: "1.2.3"
    )
    monkeypatch.setattr(release_finish, "_stage_tag", lambda *_args, **_kwargs: None)
    notes = tmp_path / "notes.md"
    notes.write_text("notes\n", encoding="utf-8")
    draft = {
        "id": 7,
        "tag_name": "v1.2.3",
        "draft": True,
        "immutable": False,
        "assets": [],
    }
    draft_page = json.dumps([draft])
    runner = QueueRunner(
        [
            cr(["gh"], draft_page),  # lint-gh-argv-literal: ok fixture assertion
            cr(["gh"]),  # lint-gh-argv-literal: ok fixture assertion
            cr(["gh"], draft_page),  # lint-gh-argv-literal: ok fixture assertion
        ]
    )
    assert (
        release_finish.stage_candidate(
            runner=runner,
            request=release_finish.CandidateRequest("1.2.3", "o/r", 5, tmp_path),
            notes_file=notes,
        )
        == SOURCE_COMMIT
    )
    assert not any(call[:3] == ["gh", "release", "create"] for call in runner.calls)  # lint-gh-argv-literal: ok fixture assertion
    list_calls = [call for call in runner.calls if "repos/o/r/releases?per_page=100" in call]
    assert len(list_calls) == 2
    assert all("--paginate" not in call for call in list_calls)


def test_release_validate_draft_rejects_incomplete_allowlist(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    identity = release_finish.assets.release_identity("1.2.3", "v1.2.3", SOURCE_COMMIT)
    incomplete = release_finish.assets.expected_asset_names(identity)[:-1]
    monkeypatch.setattr(
        release_finish, "_verify_policy", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        release_finish,
        "_pr_state",
        lambda *_args, **_kwargs: release_finish.PullRequestState(
            "OPEN", SOURCE_COMMIT
        ),
    )
    monkeypatch.setattr(
        release_finish, "_remote_tag_oid", lambda *_args, **_kwargs: SOURCE_COMMIT
    )
    monkeypatch.setattr(
        release_finish,
        "_release_state",
        lambda *_args, **_kwargs: _release_state(
            draft=True, immutable=False, names=incomplete
        ),
    )
    with pytest.raises(release_finish.ReleaseError, match="allowlist mismatch"):
        _ = release_finish.validate_release_assets(
            runner=ReleaseStateRunner(),
            candidate=_candidate(tmp_path),
            require_draft=True,
        )


def test_release_validate_draft_rejects_remote_digest_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    identity = release_finish.assets.release_identity("1.2.3", "v1.2.3", SOURCE_COMMIT)
    names = release_finish.assets.expected_asset_names(identity)
    monkeypatch.setattr(
        release_finish, "_verify_policy", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        release_finish,
        "_pr_state",
        lambda *_args, **_kwargs: release_finish.PullRequestState(
            "OPEN", SOURCE_COMMIT
        ),
    )
    monkeypatch.setattr(
        release_finish, "_remote_tag_oid", lambda *_args, **_kwargs: SOURCE_COMMIT
    )
    monkeypatch.setattr(
        release_finish,
        "_release_state",
        lambda *_args, **_kwargs: _release_state(
            draft=True, immutable=False, names=names
        ),
    )

    def download_assets(*_args, names, destination, **_kwargs):
        for name in names:
            _ = (destination / name).write_bytes(b"x")

    monkeypatch.setattr(release_finish, "_download_assets", download_assets)
    with pytest.raises(release_finish.ReleaseError, match="digest mismatch"):
        _ = release_finish.validate_release_assets(
            runner=ReleaseStateRunner(),
            candidate=_candidate(tmp_path),
            require_draft=True,
        )


def _patch_finish_common(monkeypatch: pytest.MonkeyPatch, *, draft: bool) -> list[str]:
    events: list[str] = []
    monkeypatch.setattr(
        release_finish,
        "_pr_state",
        lambda *_args, **_kwargs: release_finish.PullRequestState(
            "MERGED", SOURCE_COMMIT
        ),
    )
    monkeypatch.setattr(
        release_finish, "_plugin_version_at", lambda *_args, **_kwargs: "1.2.3"
    )
    monkeypatch.setattr(
        release_finish,
        "_release_state",
        lambda *_args, **_kwargs: _release_state(draft=draft, immutable=not draft),
    )

    def validate_assets(**_kwargs):
        events.append("validate-draft")
        return _release_state(draft=True, immutable=False)

    def verify_release(**_kwargs):
        events.append("verify-immutable")

    latest_values = iter((False, True))
    monkeypatch.setattr(release_finish, "validate_release_assets", validate_assets)
    monkeypatch.setattr(release_finish, "_verify_release_attestation", verify_release)
    monkeypatch.setattr(
        release_finish, "_is_latest", lambda *_args, **_kwargs: next(latest_values)
    )
    return events


def test_release_finish_publishes_only_after_draft_validation_and_verifies_before_latest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    events = _patch_finish_common(monkeypatch, draft=True)
    runner = ReleaseStateRunner()
    original_run = runner.run

    def recording_run(argv, **kwargs):
        if argv[:3] == ["gh", "release", "edit"]:  # lint-gh-argv-literal: ok fixture assertion
            events.append("publish" if "--draft=false" in argv else "promote-latest")
        return original_run(argv, **kwargs)

    runner.run = recording_run
    assert (
        release_finish.finish_release(
            runner=runner,
            candidate=_candidate(tmp_path),
        )
        == "publish"
    )
    assert events == ["validate-draft", "publish", "verify-immutable", "promote-latest"]


def test_release_finish_recovery_never_republishes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    events = _patch_finish_common(monkeypatch, draft=False)
    runner = ReleaseStateRunner()
    assert (
        release_finish.finish_release(
            runner=runner,
            candidate=_candidate(tmp_path),
        )
        == "resume-published"
    )
    release_edits = [call for call in runner.calls if call[:3] == ["gh", "release", "edit"]]  # lint-gh-argv-literal: ok fixture assertion
    assert len(release_edits) == 1
    assert "--latest" in release_edits[0]
    assert events == ["verify-immutable"]


def test_release_finish_rejects_candidate_not_in_main(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        release_finish,
        "_pr_state",
        lambda *_args, **_kwargs: release_finish.PullRequestState(
            "MERGED", SOURCE_COMMIT
        ),
    )
    runner = ReleaseStateRunner(ancestry_ok=False)
    with pytest.raises(release_finish.ReleaseError, match="not an ancestor"):
        _ = release_finish.finish_release(
            runner=runner,
            candidate=_candidate(tmp_path),
        )


def _write_release_version_repo(tmp_path: Path, *, cargo_version: str = "1.2.3") -> Path:
    root = tmp_path / "repo"
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin/plugin.json").write_text(
        json.dumps({"name": "larch", "version": "1.2.3"}) + "\n",
        encoding="utf-8",
    )
    (root / "plugin/.claude-plugin").mkdir(parents=True)
    _ = shutil.copy2(
        root / ".claude-plugin/plugin.json",
        root / "plugin/.claude-plugin/plugin.json",
    )
    (root / "Cargo.toml").write_text(
        f"""[workspace]
members = ["crates/larch-cli", "crates/larch-core"]

[workspace.package]
version = "{cargo_version}"

[workspace.dependencies]
larch-core = {{ version = "={cargo_version}", path = "crates/larch-core" }}
""",
        encoding="utf-8",
    )
    for name in ("larch-cli", "larch-core"):
        member = root / "crates" / name
        member.mkdir(parents=True)
        (member / "Cargo.toml").write_text(
            f'[package]\nname = "{name}"\nversion.workspace = true\n',
            encoding="utf-8",
        )
    (root / "Cargo.lock").write_text(
        f"""version = 4

[[package]]
name = "larch-cli"
version = "{cargo_version}"
dependencies = ["larch-core"]

[[package]]
name = "larch-core"
version = "{cargo_version}"
""",
        encoding="utf-8",
    )
    return root


def test_set_version_synchronizes_plugin_workspace_dependencies_and_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _write_release_version_repo(tmp_path)
    monkeypatch.setenv("LARCH_RELEASE_SET_VERSION_REPO_ROOT", str(root))

    assert version_bump.set_version_main(["1.2.4"]) == 0

    assert json.loads((root / ".claude-plugin/plugin.json").read_text())["version"] == "1.2.4"
    assert json.loads((root / "plugin/.claude-plugin/plugin.json").read_text())["version"] == "1.2.4"
    cargo = (root / "Cargo.toml").read_text(encoding="utf-8")
    assert 'version = "1.2.4"' in cargo
    assert 'larch-core = { version = "=1.2.4"' in cargo
    lock = (root / "Cargo.lock").read_text(encoding="utf-8")
    assert lock.count('version = "1.2.4"') == 2
    assert capsys.readouterr().out == "PREVIOUS_VERSION=1.2.3\nNEW_VERSION=1.2.4\n"


def test_set_version_rejects_mismatched_cargo_without_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _write_release_version_repo(tmp_path, cargo_version="1.2.2")
    paths = (root / ".claude-plugin/plugin.json", root / "Cargo.toml", root / "Cargo.lock")
    originals = {path: path.read_bytes() for path in paths}
    monkeypatch.setenv("LARCH_RELEASE_SET_VERSION_REPO_ROOT", str(root))

    assert version_bump.set_version_main(["1.2.4"]) == 1

    assert "Cargo workspace version does not match" in capsys.readouterr().err
    assert all(path.read_bytes() == originals[path] for path in paths)


def test_set_version_rolls_back_a_partial_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _write_release_version_repo(tmp_path)
    paths = (root / ".claude-plugin/plugin.json", root / "Cargo.toml", root / "Cargo.lock")
    originals = {path: path.read_bytes() for path in paths}
    real_atomic_replace = version_bump._atomic_replace
    calls = 0

    def fail_second_write(path: Path, content: bytes) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected write failure")
        real_atomic_replace(path, content)

    monkeypatch.setattr(version_bump, "_atomic_replace", fail_second_write)
    monkeypatch.setenv("LARCH_RELEASE_SET_VERSION_REPO_ROOT", str(root))

    assert version_bump.set_version_main(["1.2.4"]) == 1

    assert "release version update failed" in capsys.readouterr().err
    assert all(path.read_bytes() == originals[path] for path in paths)


def test_set_version_rejects_downgrade(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    plugin = tmp_path / "plugin.json"
    plugin.write_text(json.dumps({"version": "2.0.0"}), encoding="utf-8")
    monkeypatch.setenv("LARCH_RELEASE_SET_VERSION_PLUGIN_JSON", str(plugin))
    assert version_bump.set_version_main(["1.9.9"]) == 1
    assert "downgrade refused" in capsys.readouterr().err


def test_promote_latest_dry_run_emits_prelude(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = QueueRunner([
        cr(["gh"], json.dumps([{"tagName":"v1.2.3","isPrerelease":True,"isLatest":False,"publishedAt":"2026-01-01T00:00:00Z"}]))  # lint-gh-argv-literal: ok fixture assertion
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
        cr(["gh"]),  # lint-gh-argv-literal: ok fixture assertion
        cr(["gh"], "v1.2.3\n"),  # lint-gh-argv-literal: ok fixture assertion
        cr(["gh"], stderr="auth failed", rc=1),  # lint-gh-argv-literal: ok fixture assertion
    ])
    monkeypatch.setattr(promote_release.proc, "run", runner.run)
    assert promote_release.promote_main(["1.2.3", "--repo", "o/r"]) == 1
    assert capsys.readouterr().err.startswith("ERROR=auth failed")


def test_promote_latest_preserves_empty_boolean_fields(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = QueueRunner([
        cr(["gh"], json.dumps([{"tagName":"v1.2.3","publishedAt":"2026-01-01T00:00:00Z"}])),  # lint-gh-argv-literal: ok fixture assertion
        cr(["gh"]),  # lint-gh-argv-literal: ok fixture assertion
        cr(["gh"], json.dumps([{"tagName":"v1.2.3","isPrerelease":False,"isLatest":True}])),  # lint-gh-argv-literal: ok fixture assertion
    ])
    monkeypatch.setattr(promote_release.proc, "run", runner.run)
    assert promote_release.promote_latest_main(["--repo", "o/r"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert "RELEASE_WAS_PRERELEASE=" in out
    assert "RELEASE_WAS_LATEST=" in out
    assert "RELEASE_ALREADY_LATEST=false" in out
    assert any(call[:3] == ["gh", "release", "edit"] for call in runner.calls)  # lint-gh-argv-literal: ok fixture assertion


def test_promote_latest_verification_failure_keeps_phase_kvs(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = QueueRunner([
        cr(["gh"], json.dumps([{"tagName":"v1.2.3","isPrerelease":True,"isLatest":False,"publishedAt":"2026-01-01T00:00:00Z"}])),  # lint-gh-argv-literal: ok fixture assertion
        cr(["gh"]),  # lint-gh-argv-literal: ok fixture assertion
        cr(["gh"], json.dumps([{"tagName":"v1.2.3","isPrerelease":True,"isLatest":False}])),  # lint-gh-argv-literal: ok fixture assertion
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
        cr(["gh"], stderr="raw gh failure", rc=1),  # lint-gh-argv-literal: ok fixture assertion
    ])
    monkeypatch.setattr(promote_release.proc, "run", runner.run)
    assert promote_release.promote_latest_main(["--repo", "o/r"]) == 1
    assert capsys.readouterr().err.startswith("ERROR=raw gh failure")


def test_promote_latest_failure_ignores_inherited_quiet(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = QueueRunner([
        cr(["gh"], stderr="raw gh failure", rc=1),  # lint-gh-argv-literal: ok fixture assertion
    ])
    quiet_log = tmp_path / "quiet.log"
    monkeypatch.setenv("LARCH_QUIET_ACTIVE", "1")
    monkeypatch.setenv("LARCH_QUIET_PID", "999999")
    monkeypatch.setenv("LARCH_QUIET_LOG_FILE", str(quiet_log))
    monkeypatch.setattr(promote_release.proc, "run", runner.run)
    assert promote_release.promote_latest_main(["--repo", "o/r"]) == 1
    assert capsys.readouterr().err.startswith("ERROR=raw gh failure")
    assert not quiet_log.exists()


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
