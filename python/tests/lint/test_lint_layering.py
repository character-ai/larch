"""Detector coverage for the layering lint rule."""

from __future__ import annotations

from pathlib import Path

from larch.lint import lint_layering as lint


def _write(path: Path, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(source, encoding="utf-8")


def test_detects_higher_layer_imports_and_preserves_occurrences(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    path = python_dir / "larch" / "core" / "mod.py"
    _write(
        path,
        "from larch.state import first\n"
        "from larch.state import second\n"
        "\n"
        "def nested():\n"
        "    from larch.review import value\n",
    )

    findings = lint.scan_file(
        path,
        python_dir=python_dir,
        importer_pkg="larch.core",
        importer_tier=1,
    )

    assert [(item.qualified_symbol, item.imported_package, item.occurrence) for item in findings] == [
        ("<module>", "larch.state", 1),
        ("<module>", "larch.state", 2),
        ("nested", "larch.review", 1),
    ]


def test_relative_imports_resolve_against_importer_package(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    path = python_dir / "larch" / "core" / "mod.py"
    _write(path, "from ..state import value\n")

    findings = lint.scan_file(
        path,
        python_dir=python_dir,
        importer_pkg="larch.core",
        importer_tier=1,
    )

    assert [(item.imported_package, item.occurrence) for item in findings] == [("larch.state", 1)]


def test_iter_source_files_excludes_tests_and_generated_directories(tmp_path: Path) -> None:
    larch_dir = tmp_path / "python" / "larch"
    for relpath in [
        "core/test_mod.py",
        "core/conftest.py",
        "core/.venv/vendor.py",
        "core/__pycache__/generated.py",
        "core/prod.py",
    ]:
        _write(larch_dir / relpath, "")

    assert [path.relative_to(larch_dir.parent).as_posix() for path in lint.iter_source_files(larch_dir)] == [
        "larch/core/prod.py"
    ]
