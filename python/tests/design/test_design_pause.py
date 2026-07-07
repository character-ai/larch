# pyright: reportPrivateUsage=false, reportUnknownLambdaType=false
"""Tests for /design pause save/load port."""

from __future__ import annotations

import contextlib
import json
import io
import os
import subprocess
import stat
from pathlib import Path
from typing import TYPE_CHECKING

from larch.design import design_pause
from larch.design import design_log_publish_flow
from larch.design import design_summary

if TYPE_CHECKING:
    import pytest

# Marker delimiters mirror design_pause._PAUSE_START / _PAUSE_END (a stable wire format). Using
# literals here keeps the test from reaching into private module members; a delimiter mismatch
# would make _parse_pause_payload return no-pause-marker and fail these tests loudly.
_MARKER_START = "<!-- larch:design-pause:start -->"
_MARKER_END = "<!-- larch:design-pause:end -->"


def _git(*argv: str, cwd: Path) -> None:
    _ = subprocess.run(["git", *argv], cwd=cwd, check=True, capture_output=True)


def _write_gh_stub(path: Path, *, pr_create_rc: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(
        "#!/usr/bin/env bash\n"
        'if [ "$1" = "pr" ] && [ "$2" = "create" ]; then\n'
        f"  if [ {pr_create_rc} -ne 0 ]; then echo 'gh: pr create failed' >&2; exit {pr_create_rc}; fi\n"
        "  echo 'https://github.com/o/r/pull/77'\n"
        "  exit 0\n"
        "fi\n"
        'if [ "$1" = "pr" ] && [ "$2" = "merge" ]; then exit 0; fi\n'
        "exit 0\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _operator_repo_with_remote(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", cwd=repo)
    _git("checkout", "-q", "-b", "main", cwd=repo)
    _git("config", "user.email", "t@example.com", cwd=repo)
    _git("config", "user.name", "t", cwd=repo)
    _ = (repo / "README.md").write_text("seed\n", encoding="utf-8")
    _git("add", "README.md", cwd=repo)
    _git("commit", "-q", "-m", "seed", cwd=repo)
    origin = tmp_path / "origin.git"
    _git("init", "-q", "--bare", str(origin), cwd=tmp_path)
    _git("remote", "add", "origin", str(origin), cwd=repo)
    _git("push", "-q", "-u", "origin", "main", cwd=repo)
    return repo


def _pause_marker_body(
    *,
    run_id: str,
    issue: str,
    step: str,
    repo: str | None = None,
    recovery_branch: str | None = None,
) -> str:
    """Build an issue body carrying a design-pause marker the loader will parse."""
    lines = [
        _MARKER_START,
        f"STEP={step}",
        f"ISSUE_NUMBER={issue}",
        f"SESSION_ID={run_id}",
        f"RUN_ID={run_id}",
    ]
    if repo is not None:
        lines.append(f"REPO={repo}")
    if recovery_branch is not None:
        lines.append(f"LOG_RECOVERY_BRANCH={recovery_branch}")
    lines.append("BRAINSTORM_DONE=false")
    lines.append(_MARKER_END)
    return "\n".join(lines) + "\n"


class _FakeGit:
    """Configurable subprocess.run double for pause_load_main git + marker-delete calls."""

    def __init__(
        self,
        *,
        repo_top: str = "/repo",
        files: list[str] | None = None,
        blobs: dict[str, str] | None = None,
        verify_rc: int = 0,
        fetch_rc: int = 0,
        delete_rc: int = 0,
    ) -> None:
        self.repo_top = repo_top
        self.files = files or []
        self.blobs = blobs or {}
        self.verify_rc = verify_rc
        self.fetch_rc = fetch_rc
        self.delete_rc = delete_rc
        self.delete_called = False
        self.fetched = False

    def run(
        self, cmd: list[str], *_args: object, **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        def cp(rc: int = 0, out: str = "") -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(cmd, rc, stdout=out, stderr="")

        if "named-block" in cmd and "--delete" in cmd:
            self.delete_called = True
            return cp(self.delete_rc)
        if "rev-parse" in cmd and "--show-toplevel" in cmd:
            return cp(0, self.repo_top + "\n")
        if "fetch" in cmd:
            self.fetched = True
            return cp(self.fetch_rc)
        if "symbolic-ref" in cmd:
            return cp(0, "refs/remotes/origin/main\n")
        if "rev-parse" in cmd and "--verify" in cmd:
            return cp(self.verify_rc, "" if self.verify_rc else "deadbeefcafe\n")
        if "ls-tree" in cmd:
            return cp(0, "\x00".join(self.files))
        if "show" in cmd:
            full = cmd[-1].partition(":")[2]
            return cp(0, self.blobs.get(full, ""))
        return cp(0)


def _patch_load(
    monkeypatch: pytest.MonkeyPatch,
    body: str,
    fake: _FakeGit,
    *,
    resolve_repo: str = "owner/repo",
) -> None:
    def fake_resolve_repo(*_args: object, **_kwargs: object) -> str:
        return resolve_repo

    def fake_issue_view_body(*_args: object, **_kwargs: object) -> str:
        return body

    monkeypatch.setattr(design_pause.gh, "resolve_repo", fake_resolve_repo)  # type: ignore[attr-defined]
    monkeypatch.setattr(design_pause.gh, "issue_view_body", fake_issue_view_body)  # type: ignore[attr-defined]
    monkeypatch.setattr(design_pause.subprocess, "run", fake.run)  # type: ignore[attr-defined]


def _restore_blobs(
    run_id: str,
    *,
    issue_number: object,
    manifest_run: str,
    step: str = "3",
    completed_paths: list[str] | None = None,
) -> tuple[list[str], dict[str, str]]:
    base = f"larch-logs/design/{run_id}/"
    files = [base + "manifest.json", base + "run-params.json", base + "pause-state.txt"]
    blobs = {
        base + "manifest.json": json.dumps(
            {"issue_number": issue_number, "run_id": manifest_run}
        ),
        base + "run-params.json": "{}",
        base + "pause-state.txt": f"STEP={step}\n",
    }
    for completed_path in completed_paths or []:
        files.append(base + completed_path)
        blobs[base + completed_path] = ""
    return files, blobs


def test_pause_save_rejects_invalid_issue(tmp_path: Path, capsys: object) -> None:
    rc = design_pause.pause_save_main(
        ["--design-tmpdir", str(tmp_path), "--issue", "bad"]
    )
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert rc == 0
    assert "PAUSE_OK=false" in out
    assert "ERROR=invalid-issue" in out


def test_pause_load_no_pause_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    def fake_resolve_repo(*_args: object, **_kwargs: object) -> str:
        return "owner/repo"

    def fake_issue_view_body(*_args: object, **_kwargs: object) -> str:
        return "plain body"

    monkeypatch.setattr(design_pause.gh, "resolve_repo", fake_resolve_repo)  # type: ignore[attr-defined]
    monkeypatch.setattr(design_pause.gh, "issue_view_body", fake_issue_view_body)  # type: ignore[attr-defined]
    rc = design_pause.pause_load_main(
        ["--design-tmpdir", str(tmp_path), "--issue", "10", "--repo", "owner/repo"]
    )
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert rc == 0
    assert "LOAD_OK=false" in out
    assert "ERROR=no-pause-marker" in out


def test_pause_save_writes_marker_on_publish_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-1c").write_text("", encoding="utf-8")
    _ = (design / "source-env.sh").write_text(
        "export SESSION_ID=RUN1\nexport REPO=owner/repo\n", encoding="utf-8"
    )

    def fake_issue_view_body(*_args: object, **_kwargs: object) -> str:
        return "issue body\n"

    monkeypatch.setattr(design_pause.gh, "issue_view_body", fake_issue_view_body)  # type: ignore[attr-defined]

    calls: list[list[str]] = []

    def fake_run(
        cmd: list[str], *_args: object, **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        if "log-publish" in cmd:
            return subprocess.CompletedProcess(
                cmd, 0, stdout="PUBLISH_OK=true\n", stderr=""
            )
        if "named-block" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(design_pause.subprocess, "run", fake_run)  # type: ignore[attr-defined]
    rc = design_pause.pause_save_main(
        ["--design-tmpdir", str(design), "--issue", "9", "--repo", "owner/repo"]
    )
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert rc == 0
    publish_call = next(cmd for cmd in calls if "log-publish" in cmd)
    assert publish_call[publish_call.index("--outcome") + 1] == "paused"
    assert "PAUSE_OK=true" in out
    assert (design / "pause-state.txt").is_file()


def test_pause_save_uses_real_log_publish_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: object,
) -> None:
    repo = _operator_repo_with_remote(tmp_path)
    monkeypatch.chdir(repo)  # type: ignore[attr-defined]
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-1c").write_text("", encoding="utf-8")
    _ = (design / "source-env.sh").write_text(
        "export SESSION_ID=RUN1\nexport REPO=owner/repo\n", encoding="utf-8"
    )
    _ = (design / "artifact.txt").write_text("artifact", encoding="utf-8")
    bin_dir = tmp_path / "bin"
    _write_gh_stub(bin_dir / "gh", pr_create_rc=0)

    upsert_calls: list[list[str]] = []
    original_run_cli = design_summary._run_cli  # pyright: ignore[reportPrivateUsage]
    real_run = subprocess.run

    def fake_run_cli(*args: str) -> subprocess.CompletedProcess[str]:
        if args[:2] == ("tracking-issue", "upsert-summary"):
            upsert_calls.append(list(args))
            return subprocess.CompletedProcess(
                ["cli.py", *args], 0, stdout="", stderr=""
            )
        return original_run_cli(*args)

    def fake_render_main(argv: list[str]) -> int:
        design_tmpdir = Path(argv[argv.index("--design-tmpdir") + 1])
        session_id = (
            argv[argv.index("--session-id") + 1] if "--session-id" in argv else "RUN1"
        )
        outcome = argv[argv.index("--outcome") + 1]
        _ = (design_tmpdir / "final-summary.md").write_text(
            f"## /design run {session_id}: {outcome}\n\n"
            f"- **Outcome**: {outcome}\n"
            "<!-- larch:run-summary v=1 -->\n",
            encoding="utf-8",
        )
        return 0

    def fake_run(
        cmd: list[str], *_args: object, **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if len(cmd) >= 4 and cmd[2:4] == ["design", "log-publish"]:
            out = io.StringIO()
            err = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    subprocess.run = real_run  # type: ignore[assignment]
                    rc = design_log_publish_flow.log_publish_main(cmd[4:])
                finally:
                    subprocess.run = fake_run  # type: ignore[assignment]
            return subprocess.CompletedProcess(
                cmd, rc, stdout=out.getvalue(), stderr=err.getvalue()
            )
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ.get('PATH', '')}")  # type: ignore[attr-defined]
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[3]))  # type: ignore[attr-defined]

    def fake_issue_view_body(*_args: object, **_kwargs: object) -> str:
        return "issue body\n"

    def fake_capture_design_transcript(**_kwargs: object) -> bool:
        return True

    def fake_spawn_detached_admin_merge(**_kwargs: object) -> None:
        return None

    monkeypatch.setattr(design_pause.gh, "issue_view_body", fake_issue_view_body)  # type: ignore[attr-defined]
    monkeypatch.setattr(
        design_log_publish_flow.design_publish,
        "_capture_design_transcript",
        fake_capture_design_transcript,
    )  # type: ignore[attr-defined]
    monkeypatch.setattr(
        design_log_publish_flow,
        "_spawn_detached_admin_merge",
        fake_spawn_detached_admin_merge,
    )  # type: ignore[attr-defined]
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render_main)  # type: ignore[attr-defined]
    monkeypatch.setattr(design_summary, "_run_cli", fake_run_cli)  # type: ignore[attr-defined]  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(design_pause.subprocess, "run", fake_run)  # type: ignore[attr-defined]

    rc = design_pause.pause_save_main(
        ["--design-tmpdir", str(design), "--issue", "9", "--repo", "owner/repo"]
    )
    out = capsys.readouterr().out  # type: ignore[attr-defined]

    assert rc == 0
    assert "PAUSE_OK=true" in out
    assert not upsert_calls
    assert (design / ".design-log-publish-metadata.env").is_file()
    blob = subprocess.run(
        [
            "git",
            "show",
            "larch-logs/design-RUN1:larch-logs/design/RUN1/final-summary.md",
        ],
        cwd=tmp_path / "origin.git",
        capture_output=True,
        text=True,
        check=False,
    )
    assert blob.returncode == 0, blob.stderr
    summary_body = blob.stdout or (design / "final-summary.md").read_text(
        encoding="utf-8"
    )
    assert "## /design run" in summary_body
    assert "<!-- larch:run-summary v=1 -->" in summary_body
    assert "## /design run RUN1: paused" in summary_body


def test_pause_save_rejects_non_allowlisted_tmpdir(capsys: object) -> None:
    # Guard 6: pause-save routes --design-tmpdir through the session-tmpdir allowlist validator.
    rc = design_pause.pause_save_main(
        ["--design-tmpdir", "/nonexistent-larch-allowlist-test", "--issue", "9"]
    )
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert rc == 0
    assert "PAUSE_OK=false" in out
    assert "ERROR=tmpdir-not-allowed" in out


def test_pause_save_redacts_pause_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    # Guard 7: the local pause-state.txt payload is written through redact secrets.
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / "source-env.sh").write_text(
        "export SESSION_ID=RUN1\nexport REPO=owner/repo\n", encoding="utf-8"
    )

    def fake_issue_view_body(*_args: object, **_kwargs: object) -> str:
        return "issue body\n"

    def fake_redact_secrets_only(_text: str) -> str:
        return "REDACTED-STATE\n"

    monkeypatch.setattr(design_pause.gh, "issue_view_body", fake_issue_view_body)  # type: ignore[attr-defined]
    monkeypatch.setattr(
        design_pause.redact, "redact_secrets_only", fake_redact_secrets_only
    )  # type: ignore[attr-defined]

    def fake_run(
        cmd: list[str], *_a: object, **_k: object
    ) -> subprocess.CompletedProcess[str]:
        if "log-publish" in cmd:
            return subprocess.CompletedProcess(
                cmd, 0, stdout="PUBLISH_OK=true\n", stderr=""
            )
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(design_pause.subprocess, "run", fake_run)  # type: ignore[attr-defined]
    rc = design_pause.pause_save_main(
        ["--design-tmpdir", str(design), "--issue", "9", "--repo", "owner/repo"]
    )
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert rc == 0
    assert "PAUSE_OK=true" in out
    assert (design / "pause-state.txt").read_text(
        encoding="utf-8"
    ) == "REDACTED-STATE\n"


def test_pause_load_repo_mismatch_clears_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    # Guard 3a: a marker bound to a different repo fails closed and the stale marker is cleared.
    body = _pause_marker_body(run_id="RUN1", issue="9", step="3", repo="other/repo")
    fake = _FakeGit()
    _patch_load(monkeypatch, body, fake)
    rc = design_pause.pause_load_main(
        ["--design-tmpdir", str(tmp_path / "d"), "--issue", "9", "--repo", "owner/repo"]
    )
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert rc == 0
    assert "ERROR=repo-mismatch" in out
    assert fake.delete_called


def test_pause_load_invalid_recovery_branch_clears_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    # Guard 2: only the exact publisher branch name is accepted; anything else fails before fetch.
    body = _pause_marker_body(
        run_id="RUN1",
        issue="9",
        step="3",
        repo="owner/repo",
        recovery_branch="evil-branch",
    )
    fake = _FakeGit()
    _patch_load(monkeypatch, body, fake)
    rc = design_pause.pause_load_main(
        ["--design-tmpdir", str(tmp_path / "d"), "--issue", "9", "--repo", "owner/repo"]
    )
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert rc == 0
    assert "ERROR=invalid-recovery-branch" in out
    assert fake.delete_called
    assert not fake.fetched


def test_pause_load_rev_parse_pin_failure_keeps_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    # Guard 1: when the ref cannot be pinned to a commit SHA, fail closed but keep the marker (retryable).
    body = _pause_marker_body(run_id="RUN1", issue="9", step="3", repo="owner/repo")
    fake = _FakeGit(verify_rc=1)
    _patch_load(monkeypatch, body, fake)
    rc = design_pause.pause_load_main(
        ["--design-tmpdir", str(tmp_path / "d"), "--issue", "9", "--repo", "owner/repo"]
    )
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert rc == 0
    assert "ERROR=snapshot-not-found" in out
    assert not fake.delete_called


def test_pause_load_unsafe_restored_path_keeps_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    # Guard 4: an enumerated path that escapes the snapshot subtree is rejected before any write.
    body = _pause_marker_body(run_id="RUN1", issue="9", step="3", repo="owner/repo")
    fake = _FakeGit(files=["larch-logs/design/RUN1/../escape.txt"])
    _patch_load(monkeypatch, body, fake)
    rc = design_pause.pause_load_main(
        ["--design-tmpdir", str(tmp_path / "d"), "--issue", "9", "--repo", "owner/repo"]
    )
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert rc == 0
    assert "ERROR=unsafe-restored-path" in out
    assert not fake.delete_called


def test_pause_load_manifest_mismatch_clears_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    # Guard 3b: the restored manifest must bind to the same issue/run as the marker.
    body = _pause_marker_body(run_id="RUN1", issue="9", step="3", repo="owner/repo")
    files, blobs = _restore_blobs("RUN1", issue_number=999, manifest_run="RUN1")
    fake = _FakeGit(files=files, blobs=blobs)
    _patch_load(monkeypatch, body, fake)
    rc = design_pause.pause_load_main(
        ["--design-tmpdir", str(tmp_path / "d"), "--issue", "9", "--repo", "owner/repo"]
    )
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert rc == 0
    assert "ERROR=manifest-mismatch" in out
    assert fake.delete_called


def test_pause_load_success_deletes_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    # Guard 5 + guard 1/2 happy path: valid recovery branch, pinned SHA, full restore, marker deleted.
    body = _pause_marker_body(
        run_id="RUN1",
        issue="9",
        step="3",
        repo="owner/repo",
        recovery_branch="larch-logs/design-RUN1",
    )
    files, blobs = _restore_blobs("RUN1", issue_number=9, manifest_run="RUN1")
    fake = _FakeGit(files=files, blobs=blobs)
    _patch_load(monkeypatch, body, fake)
    dest = tmp_path / "d"
    rc = design_pause.pause_load_main(
        ["--design-tmpdir", str(dest), "--issue", "9", "--repo", "owner/repo"]
    )
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert rc == 0
    assert "LOAD_OK=true" in out
    assert "MARKER_CLEARED=true" in out
    assert fake.delete_called
    assert fake.fetched
    assert (dest / "manifest.json").is_file()


def test_pause_load_success_marker_delete_failure_warns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    # Guard 5: a post-success marker deletion failure is non-fatal (LOAD_OK stays true, WARN surfaced).
    body = _pause_marker_body(run_id="RUN1", issue="9", step="3", repo="owner/repo")
    files, blobs = _restore_blobs("RUN1", issue_number=9, manifest_run="RUN1")
    fake = _FakeGit(files=files, blobs=blobs, delete_rc=1)
    _patch_load(monkeypatch, body, fake)
    rc = design_pause.pause_load_main(
        ["--design-tmpdir", str(tmp_path / "d"), "--issue", "9", "--repo", "owner/repo"]
    )
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert rc == 0
    assert "LOAD_OK=true" in out
    assert "MARKER_CLEARED=false" in out
    assert "WARN=marker-delete-failed" in out


def test_pause_load_tolerates_manifest_without_issue_number(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    # Guard 3b tolerance: a restored manifest missing issue_number must not fail closed (null/absent
    # folds to absent, not a spurious "None" mismatch).
    body = _pause_marker_body(run_id="RUN1", issue="9", step="3", repo="owner/repo")
    base = "larch-logs/design/RUN1/"
    files = [base + "manifest.json", base + "run-params.json", base + "pause-state.txt"]
    blobs = {
        base + "manifest.json": json.dumps({"run_id": "RUN1"}),
        base + "run-params.json": "{}",
        base + "pause-state.txt": "STEP=3\n",
    }
    fake = _FakeGit(files=files, blobs=blobs)
    _patch_load(monkeypatch, body, fake)
    rc = design_pause.pause_load_main(
        ["--design-tmpdir", str(tmp_path / "d"), "--issue", "9", "--repo", "owner/repo"]
    )
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert rc == 0
    assert "LOAD_OK=true" in out


def test_determine_step_after_step3b_finalize_resumes_step4(tmp_path: Path) -> None:
    design = tmp_path / "design"
    completed = design / ".completed"
    completed.mkdir(parents=True)
    for step in ("step-3", "step-3.5", "step-3b"):
        _ = (completed / step).write_text("", encoding="utf-8")

    assert (
        design_pause._determine_step(design_tmpdir=design, plugin_root=Path.cwd())
        == "4"
    )  # pyright: ignore[reportPrivateUsage]


def test_determine_step_after_step4_resumes_gate_c_not_diagram(tmp_path: Path) -> None:
    design = tmp_path / "design"
    completed = design / ".completed"
    completed.mkdir(parents=True)
    plugin_root = Path(__file__).resolve().parents[3]
    for step in (
        "0",
        "0c",
        "1c",
        "1d",
        "1d.5",
        "1d.7",
        "1e",
        "2a",
        "2b",
        "2b.5",
        "3",
        "3.5",
        "3b",
        "4",
    ):
        _ = (completed / f"step-{step}").write_text("", encoding="utf-8")

    step = design_pause._determine_step(design_tmpdir=design, plugin_root=plugin_root)  # pyright: ignore[reportPrivateUsage]
    assert step == "4b"
    assert step != "5b.5"


def test_determine_step_routes_step5b_to_step5b5_then_step5c(tmp_path: Path) -> None:
    design = tmp_path / "design"
    completed = design / ".completed"
    completed.mkdir(parents=True)
    _ = (completed / "step-5b").write_text("", encoding="utf-8")

    assert (
        design_pause._determine_step(design_tmpdir=design, plugin_root=Path.cwd())
        == "5b.5"
    )  # pyright: ignore[reportPrivateUsage]

    _ = (completed / "step-5b.5").write_text("", encoding="utf-8")
    assert (
        design_pause._determine_step(design_tmpdir=design, plugin_root=Path.cwd())
        == "5c"
    )  # pyright: ignore[reportPrivateUsage]


def test_determine_step_returns_5b_when_step5b5_without_step5b(tmp_path: Path) -> None:
    design = tmp_path / "design"
    completed = design / ".completed"
    completed.mkdir(parents=True)
    _ = (completed / "step-5b.5").write_text("", encoding="utf-8")

    assert (
        design_pause._determine_step(design_tmpdir=design, plugin_root=Path.cwd())
        == "5b"
    )  # pyright: ignore[reportPrivateUsage]


def test_pause_load_accepts_step4b_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    body = _pause_marker_body(run_id="RUN1", issue="9", step="4b", repo="owner/repo")
    files, blobs = _restore_blobs("RUN1", issue_number="9", manifest_run="RUN1")
    fake = _FakeGit(files=files, blobs=blobs)
    _patch_load(monkeypatch, body, fake)

    rc = design_pause.pause_load_main(
        ["--design-tmpdir", str(tmp_path / "d"), "--issue", "9", "--repo", "owner/repo"]
    )

    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert rc == 0
    assert "LOAD_OK=true" in out
    assert "STEP=4b" in out


def test_pause_load_accepts_step5b_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    body = _pause_marker_body(run_id="RUN1", issue="9", step="5b", repo="owner/repo")
    files, blobs = _restore_blobs("RUN1", issue_number="9", manifest_run="RUN1")
    fake = _FakeGit(files=files, blobs=blobs)
    _patch_load(monkeypatch, body, fake)

    rc = design_pause.pause_load_main(
        ["--design-tmpdir", str(tmp_path / "d"), "--issue", "9", "--repo", "owner/repo"]
    )

    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert rc == 0
    assert "LOAD_OK=true" in out
    assert "STEP=5b" in out


def test_pause_load_restores_step5c_provenance_sentinels(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: object,
) -> None:
    body = _pause_marker_body(run_id="RUN1", issue="9", step="5c", repo="owner/repo")
    completed_paths = [
        ".completed/step-3",
        ".completed/step-5b",
        ".completed/step-5b.5",
    ]
    files, blobs = _restore_blobs(
        "RUN1",
        issue_number=9,
        manifest_run="RUN1",
        step="5c",
        completed_paths=completed_paths,
    )
    step3_result = "larch-logs/design/RUN1/.step3-review-result.env"
    files.append(step3_result)
    blobs[step3_result] = "STEP3_REVIEW_LOOP_STATUS=complete\n"
    fake = _FakeGit(files=files, blobs=blobs)
    _patch_load(monkeypatch, body, fake)

    dest = tmp_path / "d"
    rc = design_pause.pause_load_main(
        ["--design-tmpdir", str(dest), "--issue", "9", "--repo", "owner/repo"]
    )

    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert rc == 0
    assert "LOAD_OK=true" in out
    assert "STEP=5c" in out
    assert (dest / ".completed" / "step-3").is_file()
    assert (dest / ".completed" / "step-5b").is_file()
    assert (dest / ".completed" / "step-5b.5").is_file()
    assert (dest / ".step3-review-result.env").read_text(encoding="utf-8") == (
        "STEP3_REVIEW_LOOP_STATUS=complete\n"
    )


def test_pause_load_downgrades_legacy_step5c_to_step5b5(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    body = _pause_marker_body(run_id="RUN1", issue="9", step="5c", repo="owner/repo")
    base = "larch-logs/design/RUN1/"
    files = [
        base + "manifest.json",
        base + "run-params.json",
        base + "pause-state.txt",
        base + ".completed/step-5b",
    ]
    blobs = {
        base + "manifest.json": json.dumps({"issue_number": 9, "run_id": "RUN1"}),
        base + "run-params.json": "{}",
        base + "pause-state.txt": "STEP=5c\n",
        base + ".completed/step-5b": "",
    }
    fake = _FakeGit(files=files, blobs=blobs)
    _patch_load(monkeypatch, body, fake)

    dest = tmp_path / "d"
    rc = design_pause.pause_load_main(
        ["--design-tmpdir", str(dest), "--issue", "9", "--repo", "owner/repo"]
    )

    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert rc == 0
    assert "LOAD_OK=true" in out
    assert "STEP=5b.5" in out
    assert (dest / ".completed" / "step-5b").is_file()


def test_pause_load_accepts_step5b5_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    body = _pause_marker_body(run_id="RUN1", issue="9", step="5b.5", repo="owner/repo")
    files, blobs = _restore_blobs("RUN1", issue_number="9", manifest_run="RUN1")
    fake = _FakeGit(files=files, blobs=blobs)
    _patch_load(monkeypatch, body, fake)

    rc = design_pause.pause_load_main(
        ["--design-tmpdir", str(tmp_path / "d"), "--issue", "9", "--repo", "owner/repo"]
    )

    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert rc == 0
    assert "LOAD_OK=true" in out
    assert "STEP=5b.5" in out
