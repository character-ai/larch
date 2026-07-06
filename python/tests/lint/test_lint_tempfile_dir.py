from __future__ import annotations

import json
from pathlib import Path

import pytest

from larch.lint import lint_tempfile_dir as ltd


def _record(
    *,
    file: str = "larch/mod.py",
    qualified_symbol: str = "run",
    callee: str = "mkstemp",
    occurrence: int = 1,
    reason: str = "grandfathered",
    **extra: object,
) -> dict[str, object]:
    record: dict[str, object] = {
        "file": file,
        "qualified_symbol": qualified_symbol,
        "callee": callee,
        "occurrence": occurrence,
        "reason": reason,
    }
    record.update(extra)
    return record


def _write_project(root: Path, *, files: dict[str, str], baseline: object | None) -> None:
    python_dir = root / "python"
    for relpath, source in files.items():
        path = python_dir / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(source, encoding="utf-8")
    if baseline is not None:
        _ = (python_dir / ltd.BASELINE_FILENAME).write_text(json.dumps(baseline), encoding="utf-8")


def _source(body: str) -> str:
    return "import tempfile\n\ndef run():\n" + body


def test_tempfile_factories_without_dir_are_detected(tmp_path: Path) -> None:
    larch_dir = tmp_path / "python" / "larch"
    larch_dir.mkdir(parents=True)
    path = larch_dir / "mod.py"
    _ = path.write_text(
        _source(
            "    tempfile.mkstemp()\n"
            "    tempfile.mkdtemp()\n"
            "    tempfile.NamedTemporaryFile()\n"
            "    tempfile.TemporaryDirectory()\n"
        ),
        encoding="utf-8",
    )

    assert [finding.callee for finding in ltd.scan_file(path, larch_dir=larch_dir)] == [
        "mkstemp",
        "mkdtemp",
        "NamedTemporaryFile",
        "TemporaryDirectory",
    ]


def test_calls_with_dir_are_ignored_and_occurrences_count_all_calls(tmp_path: Path) -> None:
    larch_dir = tmp_path / "python" / "larch"
    larch_dir.mkdir(parents=True)
    path = larch_dir / "mod.py"
    _ = path.write_text(
        _source(
            "    tempfile.mkstemp(dir=scratch)\n"
            "    tempfile.mkstemp(\n"
            "        dir=scratch,\n"
            "    )\n"
            "    tempfile.mkstemp()\n"
        ),
        encoding="utf-8",
    )

    assert ltd.scan_file(path, larch_dir=larch_dir) == [
        ltd.Finding("larch/mod.py", "run", "mkstemp", 3, 8)
    ]


def test_with_context_expression_counts_before_nested_body_call(tmp_path: Path) -> None:
    larch_dir = tmp_path / "python" / "larch"
    larch_dir.mkdir(parents=True)
    path = larch_dir / "mod.py"
    _ = path.write_text(
        "import tempfile\n\n"
        "def run():\n"
        "    with tempfile.TemporaryDirectory() as tmp:\n"
        "        tempfile.mkdtemp(dir=tmp)\n"
        "        tempfile.NamedTemporaryFile()\n",
        encoding="utf-8",
    )

    assert [(finding.callee, finding.occurrence) for finding in ltd.scan_file(path, larch_dir=larch_dir)] == [
        ("TemporaryDirectory", 1),
        ("NamedTemporaryFile", 3),
    ]


def test_scope_excludes_tests_and_vendor_cache_dirs(tmp_path: Path) -> None:
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
        path = larch_dir / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text("import tempfile\n", encoding="utf-8")

    assert [path.relative_to(larch_dir.parent).as_posix() for path in ltd.iter_source_files(larch_dir)] == [
        "larch/prod.py"
    ]


def test_baseline_suppresses_existing_findings_reason_excluded_from_identity(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_project(
        tmp_path,
        files={"larch/mod.py": _source("    tempfile.mkstemp()\n")},
        baseline=[_record(reason="kept")],
    )

    assert ltd.main(["--root", str(tmp_path)]) == 0
    assert "warning: larch/mod.py:run calls tempfile.mkstemp occurrence 1" in capsys.readouterr().err


def test_new_finding_exits_1(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={"larch/mod.py": _source("    tempfile.mkstemp()\n")},
        baseline=[],
    )

    assert ltd.main(["--root", str(tmp_path)]) == 1


@pytest.mark.parametrize(
    "payload",
    [
        [_record(reason="")],
        [{"file": "larch/mod.py", "qualified_symbol": "run", "callee": "mkstemp", "occurrence": 1}],
        [_record(extra="nope")],
        [_record(file="python/larch/mod.py")],
        [_record(file="mod.py")],
    ],
)
def test_malformed_extra_key_empty_reason_and_bad_path_rows_exit_2(
    tmp_path: Path, payload: object
) -> None:
    _write_project(
        tmp_path,
        files={"larch/mod.py": _source("    tempfile.mkstemp()\n")},
        baseline=payload,
    )

    assert ltd.main(["--root", str(tmp_path)]) == 2


def test_duplicate_baseline_identity_exits_2(tmp_path: Path) -> None:
    row = _record()
    _write_project(
        tmp_path,
        files={"larch/mod.py": _source("    tempfile.mkstemp()\n")},
        baseline=[row, row],
    )

    assert ltd.main(["--root", str(tmp_path)]) == 2


def test_write_preserves_reasons_and_shrinks_obsolete_rows(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={"larch/mod.py": _source("    tempfile.mkstemp()\n")},
        baseline=[_record(reason="kept"), _record(callee="mkdtemp", reason="obsolete")],
    )

    assert ltd.main(["--root", str(tmp_path), "--write"]) == 0
    rows = json.loads((tmp_path / "python" / ltd.BASELINE_FILENAME).read_text(encoding="utf-8"))
    assert rows == [_record(reason="kept")]


def test_write_fails_when_new_rows_lack_reasons(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={"larch/mod.py": _source("    tempfile.mkstemp()\n    tempfile.mkdtemp()\n")},
        baseline=[_record()],
    )

    assert ltd.main(["--root", str(tmp_path), "--write"]) == 2


def test_missing_baseline_exits_2_in_check_mode(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={"larch/mod.py": _source("    tempfile.mkstemp()\n")},
        baseline=None,
    )

    assert ltd.main(["--root", str(tmp_path)]) == 2


def test_absent_baseline_bootstrap_succeeds(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={"larch/mod.py": _source("    tempfile.mkstemp()\n")},
        baseline=None,
    )

    assert ltd.main(["--root", str(tmp_path), "--write", "--initial-reason", "bootstrap"]) == 0
    rows = json.loads((tmp_path / "python" / ltd.BASELINE_FILENAME).read_text(encoding="utf-8"))
    assert rows == [_record(reason="bootstrap")]
