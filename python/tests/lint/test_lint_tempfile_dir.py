"""Detector coverage for the tempfile-dir lint rule."""

from __future__ import annotations

from pathlib import Path

from larch.lint import lint_tempfile_dir as lint


def _write_source(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text("import tempfile\n\n" + body, encoding="utf-8")


def test_detects_factories_without_dir_and_counts_all_calls(tmp_path: Path) -> None:
    larch_dir = tmp_path / "python" / "larch"
    path = larch_dir / "mod.py"
    _write_source(
        path,
        "def run(scratch):\n"
        "    tempfile.mkstemp(dir=scratch)\n"
        "    tempfile.mkdtemp()\n"
        "    tempfile.NamedTemporaryFile()\n"
        "    tempfile.TemporaryDirectory()\n",
    )

    findings = lint.scan_file(path, larch_dir=larch_dir)

    assert [(item.callee, item.occurrence) for item in findings] == [
        ("mkdtemp", 2),
        ("NamedTemporaryFile", 3),
        ("TemporaryDirectory", 4),
    ]


def test_nested_scope_and_with_context_preserve_occurrence_order(tmp_path: Path) -> None:
    larch_dir = tmp_path / "python" / "larch"
    path = larch_dir / "mod.py"
    _write_source(
        path,
        "def run():\n"
        "    with tempfile.TemporaryDirectory() as scratch:\n"
        "        tempfile.mkstemp(dir=scratch)\n"
        "        tempfile.NamedTemporaryFile()\n"
        "    def nested():\n"
        "        tempfile.mkdtemp()\n",
    )

    findings = lint.scan_file(path, larch_dir=larch_dir)

    assert [(item.qualified_symbol, item.callee, item.occurrence) for item in findings] == [
        ("run", "TemporaryDirectory", 1),
        ("run", "NamedTemporaryFile", 3),
        ("run.nested", "mkdtemp", 1),
    ]


def test_iter_source_files_omits_tests_and_generated_directories(tmp_path: Path) -> None:
    larch_dir = tmp_path / "python" / "larch"
    for relpath in [
        "test_mod.py",
        "pkg/test_nested.py",
        "conftest.py",
        "pkg/test_support.py",
        ".venv/vendor.py",
        "node_modules/vendor.py",
        "__pycache__/generated.py",
        "prod.py",
    ]:
        _write_source(larch_dir / relpath, "")

    assert [path.relative_to(larch_dir.parent).as_posix() for path in lint.iter_source_files(larch_dir)] == [
        "larch/prod.py"
    ]
