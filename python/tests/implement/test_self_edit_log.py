"""Tests for the /implement self-edit attribution log (issue #6876)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

from larch.implement import checks
from larch.implement import checks_lint_fix
from larch.implement import self_edit_log
from larch.implement.checks_run_relevant import LoopResult

if TYPE_CHECKING:
    import pytest


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    cache = tmp_path / "cache"
    session = cache / "larch" / "sessions" / "claude-implement-test"
    session.mkdir(parents=True)
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    return session


# ---- pure helpers -----------------------------------------------------------


def test_record_read_roundtrip(tmp_path: Path) -> None:
    tmp = tmp_path / "tmp"
    tmp.mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()
    _ = (repo / "a.py").write_text("A\n", encoding="utf-8")
    written = self_edit_log.record_self_edits(
        tmpdir=tmp, source="pre-commit-autofix", paths=["a.py", "b.py"], repo_root=repo, now_epoch_s=5
    )
    assert written == 2
    records = self_edit_log.read_self_edits(tmp)
    assert [r.path for r in records] == ["a.py", "b.py"]
    assert records[0].post_sha256 == _sha(b"A\n")
    assert records[1].post_sha256 == "missing"  # b.py does not exist
    assert all(r.recorded_epoch_s == 5 for r in records)
    assert records[0].source == "pre-commit-autofix"


def test_record_dedups_within_call(tmp_path: Path) -> None:
    tmp = tmp_path / "tmp"
    tmp.mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()
    written = self_edit_log.record_self_edits(
        tmpdir=tmp, source="s", paths=["a", "a", "b"], repo_root=repo
    )
    assert written == 2


def test_record_appends_single_header(tmp_path: Path) -> None:
    tmp = tmp_path / "tmp"
    tmp.mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()
    _ = self_edit_log.record_self_edits(tmpdir=tmp, source="s1", paths=["a"], repo_root=repo)
    _ = self_edit_log.record_self_edits(tmpdir=tmp, source="s2", paths=["b"], repo_root=repo)
    records = self_edit_log.read_self_edits(tmp)
    assert [(r.source, r.path) for r in records] == [("s1", "a"), ("s2", "b")]
    text = (tmp / self_edit_log.SELF_EDIT_LOG_NAME).read_text(encoding="utf-8")
    assert text.count("recorded_epoch_s\tsource\tpath\tpost_sha256") == 1


def test_record_best_effort_on_bad_input(tmp_path: Path) -> None:
    missing = tmp_path / "nope"  # not a directory
    assert self_edit_log.record_self_edits(tmpdir=missing, source="s", paths=["a"], repo_root=tmp_path) == 0
    assert self_edit_log.record_self_edits(tmpdir=tmp_path, source="s", paths=[], repo_root=tmp_path) == 0


def test_read_missing_log_is_empty(tmp_path: Path) -> None:
    assert not self_edit_log.read_self_edits(tmp_path)


def test_normalize_path_strips_control_chars() -> None:
    assert self_edit_log.normalize_path("a\tb\n") == "a b"
    assert self_edit_log.normalize_path("  x  ") == "x"


def test_digest_paths(tmp_path: Path) -> None:
    _ = (tmp_path / "a").write_text("A\n", encoding="utf-8")
    digests = self_edit_log.digest_paths(tmp_path, ["a", "gone"])
    assert digests["a"] == _sha(b"A\n")
    assert digests["gone"] == "missing"


# ---- checks self-edit-log show ---------------------------------------------


def test_show_attributed_and_content_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    session = _session(tmp_path, monkeypatch)
    repo = tmp_path / "repo"
    repo.mkdir()
    _ = (repo / "a.py").write_text("A\n", encoding="utf-8")
    _ = self_edit_log.record_self_edits(
        tmpdir=session, source="lint-fix:step3", paths=["a.py"], repo_root=repo, now_epoch_s=111
    )

    assert checks.checks_self_edit_log_main(
        ["--tmpdir", str(session), "--path", "a.py", "--repo-root", str(repo)]
    ) == 0
    out = capsys.readouterr().out
    assert "SELF_EDIT_ATTRIBUTED=true" in out
    assert "SELF_EDIT_CONTENT_MATCHES=true" in out
    assert "source=lint-fix:step3" in out
    assert "SELF_EDIT_LOG_STATUS=ok" in out

    # Content changes after the recorded self-edit -> no longer a content match.
    _ = (repo / "a.py").write_text("MUTATED\n", encoding="utf-8")
    _ = checks.checks_self_edit_log_main(
        ["--tmpdir", str(session), "--path", "a.py", "--repo-root", str(repo)]
    )
    assert "SELF_EDIT_CONTENT_MATCHES=false" in capsys.readouterr().out


def test_show_unattributed_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    session = _session(tmp_path, monkeypatch)
    repo = tmp_path / "repo"
    repo.mkdir()
    _ = self_edit_log.record_self_edits(
        tmpdir=session, source="lint-fix:step3", paths=["a.py"], repo_root=repo
    )
    assert checks.checks_self_edit_log_main(["--tmpdir", str(session), "--path", "other.py"]) == 0
    out = capsys.readouterr().out
    assert "SELF_EDIT_ATTRIBUTED=false" in out
    assert "SELF_EDIT_CONTENT_MATCHES" not in out


def test_show_dump_all(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    session = _session(tmp_path, monkeypatch)
    repo = tmp_path / "repo"
    repo.mkdir()
    _ = self_edit_log.record_self_edits(
        tmpdir=session, source="lint-fix:step3", paths=["a.py", "b.py"], repo_root=repo
    )
    assert checks.checks_self_edit_log_main(["--tmpdir", str(session)]) == 0
    out = capsys.readouterr().out
    assert "SELF_EDIT_COUNT=2" in out
    assert out.count("SELF_EDIT source=") == 2


def test_show_invalid_tmpdir(capsys: pytest.CaptureFixture[str]) -> None:
    assert checks.checks_self_edit_log_main(["--tmpdir", "/definitely/not/a/session", "--path", "a.py"]) == 2
    assert "SELF_EDIT_LOG_STATUS=tmpdir-validation" in capsys.readouterr().out


# ---- repair-loop wiring -----------------------------------------------------


def test_repair_loop_records_lint_fix_deltas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    session = _session(tmp_path, monkeypatch)
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    _ = (repo / "pkg" / "mod.py").write_text("x = 1\n", encoding="utf-8")

    def _stub_loop(**_kwargs: object) -> LoopResult:
        return LoopResult(status="ok", delta_paths=("pkg/mod.py",))

    monkeypatch.setattr(checks_lint_fix, "run_check_fix_loop", _stub_loop)
    log = session / "checks.log"
    _ = log.write_text("stub\n", encoding="utf-8")

    rc = checks.checks_repair_loop_main(
        ["--tmpdir", str(session), "--site", "step3", "--checks-log", str(log), "--repo-root", str(repo)]
    )
    _ = capsys.readouterr()
    assert rc == 0
    records = self_edit_log.read_self_edits(session)
    assert [r.path for r in records] == ["pkg/mod.py"]
    assert records[0].source == "lint-fix:step3"
    assert records[0].post_sha256 == _sha(b"x = 1\n")
