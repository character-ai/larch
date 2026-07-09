from __future__ import annotations

import json
from pathlib import Path

import pytest

from larch.lint import lint_renderer_golden_tests as lrgt


def _record(
    *,
    file: str = "larch/report/progress_report.py",
    function_name: str = "_render_progress",
    reason: str = "grandfathered",
    **extra: object,
) -> dict[str, object]:
    record: dict[str, object] = {"file": file, "function_name": function_name, "reason": reason}
    record.update(extra)
    return record


def _write_project(root: Path, *, files: dict[str, str], baseline: object | None = None) -> None:
    python_dir: Path = root / "python"
    for relpath, source in files.items():
        path: Path = python_dir / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(source, encoding="utf-8")
    if baseline is not None:
        baseline_path: Path = python_dir / lrgt.BASELINE_FILENAME
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        _ = baseline_path.write_text(json.dumps(baseline), encoding="utf-8")


def _report_function(name: str = "_render_progress", *, suffix: str = "") -> str:
    return f"def {name}() -> str:\n    return 'ok'\n{suffix}"


def test_violating_report_function_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_project(
        tmp_path,
        files={"larch/report/progress_report.py": _report_function()},
        baseline=[],
    )

    assert lrgt.main(["--root", str(tmp_path)]) == 1
    assert "larch/report/progress_report.py:_render_progress" in capsys.readouterr().err


def test_clean_report_function_referenced_from_report_test_exits_0(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/report/progress_report.py": _report_function(),
            "tests/report/test_progress_report.py": "def test_ref() -> None:\n    assert '_render_progress'\n",
        },
        baseline=[],
    )

    assert lrgt.main(["--root", str(tmp_path)]) == 0


def test_same_line_suppression_with_reason_exits_0(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/report/progress_report.py": (
                "def _render_progress() -> str:  # lint-renderer-golden-tests: ok fixture\n"
                "    return 'ok'\n"
            )
        },
        baseline=[],
    )

    assert lrgt.main(["--root", str(tmp_path)]) == 0


def test_same_line_suppression_without_reason_does_not_suppress(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/report/progress_report.py": (
                "def _render_progress() -> str:  # lint-renderer-golden-tests: ok\n"
                "    return 'ok'\n"
            )
        },
        baseline=[],
    )

    assert lrgt.main(["--root", str(tmp_path)]) == 1


def test_baseline_row_suppresses_live_finding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_project(
        tmp_path,
        files={"larch/report/progress_report.py": _report_function()},
        baseline=[_record(reason="kept")],
    )

    assert lrgt.main(["--root", str(tmp_path)]) == 0
    assert "baselined" in capsys.readouterr().err


def test_new_unbaselined_renderer_fails_while_baselined_renderer_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/report/progress_report.py": _report_function(),
            "larch/report/timing.py": _report_function("_render_timing"),
        },
        baseline=[_record(reason="kept")],
    )

    assert lrgt.main(["--root", str(tmp_path)]) == 1
    stderr: str = capsys.readouterr().err
    assert "larch/report/progress_report.py:_render_progress" in stderr
    assert "larch/report/timing.py:_render_timing" in stderr


def test_write_with_initial_reason_writes_canonical_json(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={"larch/report/progress_report.py": _report_function()},
    )

    assert lrgt.main(
        ["--root", str(tmp_path), "--write", "--initial-reason", "bootstrap reason"]
    ) == 0
    rows: object = json.loads(
        (tmp_path / "python" / lrgt.BASELINE_FILENAME).read_text(encoding="utf-8")
    )
    assert rows == [_record(reason="bootstrap reason")]


def test_routine_write_preserves_existing_reasons(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={"larch/report/progress_report.py": _report_function()},
        baseline=[_record(reason="preserved")],
    )

    assert lrgt.main(["--root", str(tmp_path), "--write"]) == 0
    rows: object = json.loads(
        (tmp_path / "python" / lrgt.BASELINE_FILENAME).read_text(encoding="utf-8")
    )
    assert rows == [_record(reason="preserved")]


def test_stale_baseline_row_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_project(
        tmp_path,
        files={"larch/report/progress_report.py": _report_function()},
        baseline=[_record(file="larch/report/missing.py", function_name="_render_missing")],
    )

    assert lrgt.main(["--root", str(tmp_path)]) == 1
    assert "stale baseline row: larch/report/missing.py:_render_missing" in capsys.readouterr().err


def test_stale_baseline_function_name_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_project(
        tmp_path,
        files={"larch/report/progress_report.py": _report_function()},
        baseline=[_record(function_name="helper")],
    )

    assert lrgt.main(["--root", str(tmp_path)]) == 1
    assert "stale baseline row: larch/report/progress_report.py:helper" in capsys.readouterr().err


@pytest.mark.parametrize(
    "baseline",
    [
        [{"file": "larch/report/progress_report.py", "function_name": "_render_progress"}],
        [_record(extra="bad")],
        [_record(), _record()],
        [_record(file="../escape.py")],
        [_record(function_name="")],
    ],
)
def test_malformed_baseline_rows_fail_exit_2(tmp_path: Path, baseline: object) -> None:
    _write_project(
        tmp_path,
        files={"larch/report/progress_report.py": _report_function()},
        baseline=baseline,
    )

    assert lrgt.main(["--root", str(tmp_path)]) == 2


def test_scope_ignores_nested_non_report_test_symlink_and_non_matching_functions(
    tmp_path: Path,
) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/report/progress_report.py": (
                "def wrapper() -> None:\n"
                "    def _render_nested() -> str:\n"
                "        return 'nested'\n"
                "def helper() -> str:\n"
                "    return 'ok'\n"
            ),
            "larch/not_report.py": _report_function(),
            "tests/report/test_progress_report.py": _report_function("_render_test_only"),
        },
        baseline=[],
    )
    symlink_path: Path = tmp_path / "python" / "larch" / "report" / "linked.py"
    target_path: Path = tmp_path / "python" / "larch" / "not_report.py"
    try:
        symlink_path.symlink_to(target_path)
    except OSError:
        pytest.skip("filesystem does not support symlinks")

    assert lrgt.main(["--root", str(tmp_path)]) == 0
    report_dir: Path = tmp_path / "python" / "larch" / "report"
    assert "linked.py" not in [path.name for path in lrgt.iter_report_files(report_dir)]


def test_non_utf8_test_source_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/report/progress_report.py": _report_function(),
            "tests/report/test_progress_report.py": _report_function(),
        },
        baseline=[],
    )
    _ = (tmp_path / "python" / "tests" / "report" / "test_progress_report.py").write_bytes(b"\xff\xfe")

    assert lrgt.main(["--root", str(tmp_path)]) == 2
    assert "cannot read source" in capsys.readouterr().err


def test_non_utf8_baseline_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_project(
        tmp_path,
        files={"larch/report/progress_report.py": _report_function()},
        baseline=[],
    )
    _ = (tmp_path / "python" / lrgt.BASELINE_FILENAME).write_bytes(b"\xff\xfe")

    assert lrgt.main(["--root", str(tmp_path)]) == 2
    assert "cannot read baseline" in capsys.readouterr().err


def test_whole_identifier_matching_is_required(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/report/tokens.py": _report_function("_vendor_rows"),
            "tests/report/test_tokens.py": "# _progress_vendor_rows is a different helper\n",
        },
        baseline=[],
    )

    assert lrgt.main(["--root", str(tmp_path)]) == 1


def test_identifier_boundary_reference_is_enough(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/report/tokens.py": _report_function("_vendor_rows"),
            "tests/report/test_tokens.py": "# coverage reference: _vendor_rows\n",
        },
        baseline=[],
    )

    assert lrgt.main(["--root", str(tmp_path)]) == 0


def test_write_fails_when_new_rows_lack_reasons(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/report/progress_report.py": _report_function(),
            "larch/report/timing.py": _report_function("_render_timing"),
        },
        baseline=[_record(reason="kept")],
    )

    assert lrgt.main(["--root", str(tmp_path), "--write"]) == 2
    err: str = capsys.readouterr().err
    assert "missing baseline reasons" in err
    assert "larch/report/timing.py:_render_timing" in err


def test_parse_failure_exits_2(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={"larch/report/broken.py": "def _render_broken(:\n"},
        baseline=[],
    )

    assert lrgt.main(["--root", str(tmp_path)]) == 2
