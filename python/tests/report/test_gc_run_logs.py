from __future__ import annotations
# pyright: reportUnusedCallResult=false

import hashlib
import json
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest  # noqa: TC002

from larch.report import gc_run_logs
from larch.core.proc import CommandResult
from larch.report.report_tokens_scan import scan


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


def test_gc_run_logs_naive_started_at_dry_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _repo(tmp_path)
    _run_dir(repo, "naive-date", started_at="2020-01-01T00:00:00")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "run")
    monkeypatch.chdir(repo)
    assert gc_run_logs.run_main(["--dry-run", "--older-than", "90"]) == 0
    out = capsys.readouterr().out
    assert "DIRS_QUALIFYING=1" in out
    assert "STATUS=ok" in out


def test_gc_run_logs_skips_escape_symlink(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _repo(tmp_path)
    run = _run_dir(repo, "escape")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret\n", encoding="utf-8")
    (run / "escape-link").symlink_to(outside)
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "run")
    monkeypatch.chdir(repo)
    assert gc_run_logs.run_main(["--dry-run", "--older-than", "90"]) == 0
    out = capsys.readouterr().out
    assert "DIRS_QUALIFYING=0" in out
    assert "DIRS_SKIPPED=1" in out


def test_gc_run_logs_git_date_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _repo(tmp_path)
    run = repo / "larch-logs" / "implement" / "no-manifest"
    run.mkdir(parents=True)
    (run / "final-summary.md").write_text("summary\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "run", "--date", "2020-01-01T00:00:00Z")
    monkeypatch.chdir(repo)
    assert gc_run_logs.run_main(["--dry-run", "--older-than", "90"]) == 0
    out = capsys.readouterr().out
    assert "DIRS_QUALIFYING=1" in out


def test_gc_run_logs_apply_failure_emits_recovery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _repo(tmp_path)
    _run_dir(repo, "old")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "run")
    monkeypatch.chdir(repo)

    def fail_apply(*_args: object, **_kwargs: object) -> str:
        raise RuntimeError("apply failed")

    monkeypatch.setattr(gc_run_logs, "_apply", fail_apply)
    assert gc_run_logs.run_main(["--older-than", "90"]) == 2
    err = capsys.readouterr().err
    assert "git checkout main" in err


def test_gc_run_logs_slim_apply_keeps_core_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _repo(tmp_path)
    run = _run_dir(repo, "old")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "run")
    monkeypatch.chdir(repo)

    def fake_apply(
        *,
        repo_root: Path,
        logs_root: Path,
        plan: list[gc_run_logs.PlannedDir],
        counters: gc_run_logs.Counters,
        older_than: int,
        delete: bool,
        cutoff_dt: str,
    ) -> str:
        _ = repo_root, logs_root, older_than, delete, cutoff_dt
        for item in plan:
            forensic = item.path / "forensic.txt"
            if forensic.is_file():
                forensic.unlink()
            (item.path / "gc-slimmed").write_text(item.run_date + "\n", encoding="utf-8")
            counters.slimmed += 1
        return "https://example.invalid/pr/1"

    monkeypatch.setattr(gc_run_logs, "_apply", fake_apply)
    assert gc_run_logs.run_main(["--older-than", "90"]) == 0
    assert (run / "final-summary.md").is_file()
    assert (run / "gc-slimmed").is_file()
    assert not (run / "forensic.txt").exists()


def test_keep_file_retains_design_token_ledger() -> None:
    # issue #5133: the committed token ledger is the only priceable source for
    # design runs that never finalized token-report-final.json, so slimming must
    # retain it (design only).
    keep = gc_run_logs._keep_file  # pyright: ignore[reportPrivateUsage]
    assert keep(filename="larch-tokens-deadbeef.jsonl", skill="design")
    assert not keep(filename="larch-tokens-deadbeef.jsonl", skill="implement")
    assert not keep(filename="scratch.txt", skill="design")
    assert keep(filename="manifest.json", skill="design")
    assert keep(filename="session-id", skill="design")
    assert keep(filename="architectural-guideline-assessment.md", skill="design")
    assert not keep(filename="architectural-guideline-assessment.md", skill="implement")
    assert keep(filename="architectural-guideline-outcome.json", skill="implement")
    assert not keep(filename="architectural-guideline-outcome.json", skill="design")
    assert not keep(filename="session-id", skill="implement")


@dataclass
class _ScanRunner:
    root: Path

    def run(self, argv: Sequence[str], **_kwargs: object) -> CommandResult:
        if list(argv)[:2] == ["git", "rev-parse"]:
            return CommandResult(tuple(argv), 0, str(self.root), "", 0.0)
        return CommandResult(tuple(argv), 1, "", "gh transient failure", 0.0)


def test_gc_run_logs_slim_preserves_design_guideline_assessment(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    logs_root = repo / "larch-logs"
    run = logs_root / "design" / "with-assessment"
    run.mkdir(parents=True)
    assessment = "Deviation approved for the final plan.\n"
    _ = (run / "manifest.json").write_text('{"started_at":"2020-01-01T00:00:00Z"}\n', encoding="utf-8")
    _ = (run / "final-summary.md").write_text("summary\n", encoding="utf-8")
    _ = (run / "architectural-guideline-assessment.md").write_text(assessment, encoding="utf-8")
    _ = (run / "forensic.txt").write_text("x" * 10, encoding="utf-8")
    (run / "round-1").mkdir()
    _ = (run / "round-1" / "detail.txt").write_text("detail\n", encoding="utf-8")

    item = gc_run_logs.PlannedDir("design", run, "2020-01-01T00:00:00Z")
    _ = gc_run_logs._slim_dir(logs_root=logs_root, item=item)  # pyright: ignore[reportPrivateUsage]

    assert (run / "architectural-guideline-assessment.md").read_text(encoding="utf-8") == assessment
    assert not (run / "forensic.txt").exists()
    assert (run / "gc-slimmed").is_file()


def test_gc_run_logs_slim_preserves_session_id_for_multi_ledger_recovery(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    logs_root = repo / "larch-logs"
    run = logs_root / "design" / "multi-ledger"
    run.mkdir(parents=True)
    session_id = "scoped-session-42"
    slug = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
    scoped_rows = [
        {"type": "mark", "step": "design Step 0", "ts": "2026-06-15T00:00:00Z"},
        {"type": "vendor", "vendor": "codex", "input": 10, "output": 1, "total": 11, "ts": "2026-06-15T00:00:05Z"},
    ]
    orphan_rows = [
        {"type": "mark", "step": "design Step 0", "ts": "2026-06-15T00:00:00Z"},
        {"type": "vendor", "vendor": "codex", "input": 900, "output": 90, "total": 990, "ts": "2026-06-15T00:00:05Z"},
    ]
    _ = (run / "manifest.json").write_text(json.dumps({"started_at": "2020-01-01T00:00:00Z", "issue_number": 10}), encoding="utf-8")
    _ = (run / "final-summary.md").write_text("summary\n", encoding="utf-8")
    _ = (run / "session-id").write_text(session_id, encoding="utf-8")
    _ = (run / f"larch-tokens-{slug}.jsonl").write_text(
        "\n".join(json.dumps(row) for row in scoped_rows) + "\n",
        encoding="utf-8",
    )
    _ = (run / "larch-tokens-orphan.jsonl").write_text(
        "\n".join(json.dumps(row) for row in orphan_rows) + "\n",
        encoding="utf-8",
    )
    _ = (run / "forensic.txt").write_text("x" * 10, encoding="utf-8")
    (run / "round-1").mkdir()
    _ = (run / "round-1" / "detail.txt").write_text("detail\n", encoding="utf-8")

    item = gc_run_logs.PlannedDir("design", run, "2020-01-01T00:00:00Z")
    _ = gc_run_logs._slim_dir(logs_root=logs_root, item=item)  # pyright: ignore[reportPrivateUsage]

    assert (run / "session-id").is_file()
    assert (run / f"larch-tokens-{slug}.jsonl").is_file()
    assert (run / "larch-tokens-orphan.jsonl").is_file()
    assert not (run / "forensic.txt").exists()
    assert not (run / "round-1").exists()
    assert (run / "gc-slimmed").is_file()

    result = scan(_ScanRunner(repo), skill="design", repo_override="o/r")
    assert len(result.records) == 1
    assert result.records[0].codex.total == 11



def test_keep_file_retains_checks_digest_sizes_for_implement_and_review() -> None:
    keep = gc_run_logs._keep_file  # pyright: ignore[reportPrivateUsage]

    assert keep(filename="checks-digest-sizes.tsv", skill="implement")
    assert keep(filename="checks-digest-sizes.tsv", skill="review")
    assert not keep(filename="checks-digest-sizes.tsv", skill="design")


def test_gc_run_logs_slim_preserves_checks_digest_sizes_for_implement_and_review(tmp_path: Path) -> None:
    logs_root = tmp_path / "repo" / "larch-logs"
    for skill in ("implement", "review"):
        run = logs_root / skill / "run-abc"
        run.mkdir(parents=True)
        (run / "manifest.json").write_text('{"started_at":"2020-01-01T00:00:00Z"}\n', encoding="utf-8")
        (run / "final-summary.md").write_text("summary\n", encoding="utf-8")
        (run / "checks-digest-sizes.tsv").write_text("site\tattempt\nstep6\t1\n", encoding="utf-8")
        (run / "forensic.txt").write_text("remove me\n", encoding="utf-8")

        item = gc_run_logs.PlannedDir(skill, run, "2020-01-01T00:00:00Z")
        _ = gc_run_logs._slim_dir(logs_root=logs_root, item=item)  # pyright: ignore[reportPrivateUsage]

        assert (run / "checks-digest-sizes.tsv").is_file()
        assert not (run / "forensic.txt").exists()
        assert (run / "gc-slimmed").is_file()


def test_keep_file_retains_difficulty_rating() -> None:
    keep = gc_run_logs._keep_file  # pyright: ignore[reportPrivateUsage]

    assert keep(filename="difficulty-rating.json", skill="implement")
    assert keep(filename="difficulty-rating.json", skill="design")
    assert keep(filename="difficulty-rating.json", skill="review")
