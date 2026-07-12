"""Tests for lint run-log-walkers."""

from __future__ import annotations

from pathlib import Path

from larch.lint import lint_run_log_walkers as lint


def test_scan_rejects_raw_glob_and_dual_manifest() -> None:
    source = """
from pathlib import Path
def walk(log_root: Path) -> None:
    for path in log_root.glob("implement/*/round-*/findings-classification.tsv"):
        print(path)
    for name in ("manifest.json", "run-manifest.json"):
        data = (log_root / name).read_text()
        print(data)
"""
    findings = lint.scan_source(relpath="larch/example.py", source=source)
    rules = {finding.rule for finding in findings}
    assert "classification-glob" in rules
    assert "dual-manifest-loop" in rules


def test_scan_rejects_raw_walk_and_scandir() -> None:
    source = """
import os
from pathlib import Path
def walk(log_root: Path) -> None:
    for root, dirs, files in os.walk(log_root):
        print(root, dirs, files)
    with os.scandir(log_root) as entries:
        print(list(entries))
"""
    findings = lint.scan_source(relpath="larch/example.py", source=source)
    rules = {finding.rule for finding in findings}
    assert "raw-walk" in rules
    assert "raw-scandir" in rules


def test_scan_allows_shared_helpers_and_fixed_artifact_reads() -> None:
    source = """
from pathlib import Path
from larch.report import run_log_corpus
def ok(log_root: Path) -> None:
    for run_dir in run_log_corpus.safe_child_run_dirs(log_root):
        manifest = run_dir / "manifest.json"
        print(manifest.read_text())
        for path in run_log_corpus.iter_validated_run_files(run_dir, name="panel-prompt-sizes.tsv"):
            print(path)
"""
    assert lint.scan_source(relpath="larch/example.py", source=source) == []


def test_scan_allows_session_local_and_unrelated_traversal() -> None:
    source = """
from pathlib import Path
def local(implement_tmpdir: Path) -> None:
    for path in implement_tmpdir.glob("round-*/scout-*.json"):
        print(path)
def unrelated(skills: Path) -> None:
    for path in skills.glob("*/scripts/test-*.sh"):
        print(path)
"""
    assert lint.scan_source(relpath="larch/example.py", source=source) == []


def test_owner_and_exemptions_are_skipped(tmp_path: Path, monkeypatch: object) -> None:
    root = tmp_path
    owner = root / "python" / "larch" / "report" / "run_log_corpus.py"
    owner.parent.mkdir(parents=True)
    _ = owner.write_text(
        'from pathlib import Path\n'
        'def bad(log_root: Path) -> None:\n'
        '    list(log_root.glob("*"))\n',
        encoding="utf-8",
    )
    exempt = root / "python" / "larch" / "report" / "retro_fix_cursor.py"
    _ = exempt.write_text(
        'from pathlib import Path\n'
        'def bad(log_root: Path) -> None:\n'
        '    list(log_root.glob("*"))\n',
        encoding="utf-8",
    )
    skill = root / "skills" / "fluff-analysis" / "scripts" / "fluff-analysis.py"
    skill.parent.mkdir(parents=True)
    _ = skill.write_text("print('ok')\n", encoding="utf-8")

    def _tracked(_root: Path) -> list[str]:
        return [
            "python/larch/report/run_log_corpus.py",
            "python/larch/report/retro_fix_cursor.py",
            "skills/fluff-analysis/scripts/fluff-analysis.py",
        ]

    monkeypatch.setattr(lint, "_tracked_python_relpaths", _tracked)  # type: ignore[attr-defined]
    assert lint.collect_findings(root) == []


def test_main_returns_zero_when_clean(tmp_path: Path, monkeypatch: object) -> None:
    monkeypatch.setattr(lint, "collect_findings", lambda _root: [])  # type: ignore[attr-defined]
    assert lint.main(["--root", str(tmp_path)]) == 0


def test_main_returns_one_with_stable_diagnostics(tmp_path: Path, monkeypatch: object, capsys: object) -> None:
    finding = lint.Finding(
        file="python/larch/example.py",
        lineno=12,
        rule="raw-glob",
        message="use run_log_corpus.safe_child_run_dirs instead of raw corpus Path.glob",
    )
    monkeypatch.setattr(lint, "collect_findings", lambda _root: [finding])  # type: ignore[attr-defined]
    assert lint.main(["--root", str(tmp_path)]) == 1
    err = capsys.readouterr().err  # type: ignore[attr-defined]
    assert "python/larch/example.py:12: [raw-glob]" in err
    assert "Remediation:" in err
