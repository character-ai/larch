from __future__ import annotations
# pyright: reportUnusedCallResult=false

import subprocess
from pathlib import Path

import pytest  # noqa: TC002

import gc_run_logs


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Test")
    (repo / "larch-logs" / "implement").mkdir(parents=True)
    (repo / "README.md").write_text("repo\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "init")
    return repo


def _run_dir(repo: Path, name: str, started_at: str = "2020-01-01T00:00:00Z") -> Path:
    run = repo / "larch-logs" / "implement" / name
    run.mkdir(parents=True)
    (run / "manifest.json").write_text(f'{{"started_at":"{started_at}"}}\n', encoding="utf-8")
    (run / "final-summary.md").write_text("summary\n", encoding="utf-8")
    (run / "forensic.txt").write_text("x" * 10, encoding="utf-8")
    (run / "round-1").mkdir()
    (run / "round-1" / "detail.txt").write_text("detail\n", encoding="utf-8")
    return run


def test_gc_run_logs_dry_run_no_mutation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _repo(tmp_path)
    run = _run_dir(repo, "old")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "run")
    monkeypatch.chdir(repo)
    rc = gc_run_logs.run_main(["--dry-run", "--older-than", "90"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "DIRS_SCANNED=1" in out
    assert "DIRS_QUALIFYING=1" in out
    assert "DRY_RUN=true" in out
    assert "STATUS=ok" in out
    assert (run / "forensic.txt").exists()
    assert not (run / "gc-slimmed").exists()


def test_gc_run_logs_guard_dirty_before_scan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _repo(tmp_path)
    _run_dir(repo, "old")
    monkeypatch.chdir(repo)
    assert gc_run_logs.run_main(["--dry-run"]) == 2
    out = capsys.readouterr().out
    assert out.strip() == "STATUS=error"


def test_gc_run_logs_requires_main(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _repo(tmp_path)
    _git(repo, "checkout", "-b", "feature")
    monkeypatch.chdir(repo)
    assert gc_run_logs.run_main(["--dry-run"]) == 2
    assert "STATUS=error" in capsys.readouterr().out


def test_gc_run_logs_skips_paused_and_slimmed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _repo(tmp_path)
    paused = _run_dir(repo, "paused")
    (paused / "pause-state.txt").write_text("paused\n", encoding="utf-8")
    slimmed = _run_dir(repo, "slimmed")
    (slimmed / "gc-slimmed").write_text("old\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "runs")
    monkeypatch.chdir(repo)
    assert gc_run_logs.run_main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "DIRS_SCANNED=2" in out
    assert "DIRS_QUALIFYING=0" in out
    assert "DIRS_SKIPPED=2" in out


def test_gc_run_logs_invalid_older_than(capsys: pytest.CaptureFixture[str]) -> None:
    assert gc_run_logs.run_main(["--older-than", "0"]) == 2
    assert "STATUS=error" in capsys.readouterr().out
