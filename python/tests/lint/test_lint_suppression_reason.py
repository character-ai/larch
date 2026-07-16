from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from larch.lint import lint_suppression_reason as lsr


def _git_init(root: Path) -> None:
    _ = subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    _ = subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    _ = subprocess.run(["git", "config", "user.name", "test"], cwd=root, check=True)
    _ = subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    _ = subprocess.run(
        ["git", "commit", "-q", "-m", "fixture", "--allow-empty"], cwd=root, check=True
    )


def _record(
    *,
    file: str = "larch/mod.py",
    suppression_kind: str = lsr.KIND_NOQA,
    text: str = "noqa",
    occurrence: int = 1,
    reason: str = "grandfathered",
    **extra: object,
) -> dict[str, object]:
    record: dict[str, object] = {
        "file": file,
        "suppression_kind": suppression_kind,
        "text": text,
        "occurrence": occurrence,
        "reason": reason,
    }
    record.update(extra)
    return record


def _write_project(root: Path, *, files: dict[str, str], baseline: object | None = None) -> None:
    python_dir = root / "python"
    for relpath, source in files.items():
        path = python_dir / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(source, encoding="utf-8")
    if baseline is not None:
        baseline_path = python_dir / lsr.BASELINE_FILENAME
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        _ = baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    _git_init(root)


def _module(comment: str) -> str:
    return f"from __future__ import annotations\n\nVALUE = 1  {comment}\n"


def _scan_comment(tmp_path: Path, comment: str) -> list[lsr.Finding]:
    python_dir = tmp_path / "python"
    path = python_dir / "larch" / "mod.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(_module(comment), encoding="utf-8")
    return lsr.scan_file(path, python_dir=python_dir)


@pytest.mark.parametrize(
    ("comment", "kind", "text"),
    [
        ("# noqa", lsr.KIND_NOQA, "noqa"),
        ("# noqa: E501", lsr.KIND_NOQA, "noqa: E501"),
        ("# noqa: E501 -", lsr.KIND_NOQA, "noqa: E501 -"),
        ("# ruff: noqa", lsr.KIND_RUFF_NOQA, "ruff: noqa"),
        ("# ruff: noqa: F401", lsr.KIND_RUFF_NOQA, "ruff: noqa: F401"),
        ("# pylint: disable=unused-argument", lsr.KIND_PYLINT_DISABLE, "pylint: disable=unused-argument"),
        (
            "# pylint: disable-next=protected-access",
            lsr.KIND_PYLINT_DISABLE_NEXT,
            "pylint: disable-next=protected-access",
        ),
        ("# pylint: skip-file", lsr.KIND_PYLINT_SKIP_FILE, "pylint: skip-file"),
        ("# type: ignore", lsr.KIND_TYPE_IGNORE, "type: ignore"),
        ("# type: ignore[assignment]", lsr.KIND_TYPE_IGNORE, "type: ignore[assignment]"),
        ("# pyright: ignore", lsr.KIND_PYRIGHT_IGNORE, "pyright: ignore"),
        (
            "# pyright: ignore[reportPrivateUsage]",
            lsr.KIND_PYRIGHT_IGNORE,
            "pyright: ignore[reportPrivateUsage]",
        ),
        ("# pyright: reportMissingImports=false", lsr.KIND_PYRIGHT_REPORT, "pyright: reportMissingImports=false"),
    ],
)
def test_missing_reason_forms_are_detected(
    tmp_path: Path, comment: str, kind: str, text: str
) -> None:
    assert _scan_comment(tmp_path, comment) == [lsr.Finding("larch/mod.py", kind, text, 1, 3)]


@pytest.mark.parametrize(
    "comment",
    [
        "# noqa: E501 - long fixture line",
        "# ruff: noqa: F401 - imported for public API",
        "# pylint: disable=unused-argument  # protocol signature keeps this name",
        "# pylint: disable-next=protected-access  # fixture inspects private state",
        "# pylint: skip-file  # generated compatibility module",
        "# type: ignore[assignment]  # typed fixture narrows at runtime",
        "# pyright: ignore[reportPrivateUsage]  # fixture inspects private state",
        "# pyright: reportMissingImports=false  # optional dependency imported in production",
        "# pyright: reportMissingImports=false, reportPrivateUsage=false  # optional dependency imported in production",
    ],
)
def test_reason_bearing_forms_pass(tmp_path: Path, comment: str) -> None:
    assert not _scan_comment(tmp_path, comment)


def test_adjacent_preceding_reason_does_not_suppress_finding(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    path = python_dir / "larch" / "mod.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(
        "from __future__ import annotations\n\n"
        "# reason: fixture keeps broad skip\n"
        "# pylint: skip-file\n"
        "VALUE = 1\n",
        encoding="utf-8",
    )

    assert lsr.scan_file(path, python_dir=python_dir) == [
        lsr.Finding("larch/mod.py", lsr.KIND_PYLINT_SKIP_FILE, "pylint: skip-file", 1, 4)
    ]


def test_chained_suppressions_fail_without_individual_reasons(tmp_path: Path) -> None:
    findings = _scan_comment(
        tmp_path,
        "# noqa: SLF001  # pyright: ignore[reportPrivateUsage]",
    )

    assert findings == [
        lsr.Finding("larch/mod.py", lsr.KIND_NOQA, "noqa: SLF001", 1, 3),
        lsr.Finding(
            "larch/mod.py",
            lsr.KIND_PYRIGHT_IGNORE,
            "pyright: ignore[reportPrivateUsage]",
            1,
            3,
        ),
    ]


def test_reason_may_mention_suppression_when_non_suppression_text_remains(tmp_path: Path) -> None:
    assert not _scan_comment(
        tmp_path,
        "# pylint: disable=unused-argument  # pyright: ignore[reportUnusedParameter] is documented",
    )


def test_chained_suppressions_pass_with_individual_reasons(tmp_path: Path) -> None:
    findings = _scan_comment(
        tmp_path,
        "# pylint: disable=unused-argument  # protocol shape # type: ignore[override]  # fixture override",
    )

    assert not findings


def test_semicolon_delimited_comment_scans_later_suppressions(tmp_path: Path) -> None:
    assert _scan_comment(
        tmp_path,
        "# formatter note; noqa; pyright: ignore[reportPrivateUsage]",
    ) == [
        lsr.Finding("larch/mod.py", lsr.KIND_NOQA, "noqa", 1, 3),
        lsr.Finding(
            "larch/mod.py",
            lsr.KIND_PYRIGHT_IGNORE,
            "pyright: ignore[reportPrivateUsage]",
            1,
            3,
        ),
    ]


def test_embedded_hash_reason_keeps_later_suppression(tmp_path: Path) -> None:
    assert _scan_comment(
        tmp_path,
        "# pylint: disable=unused-argument  # protocol shape # hash note # pyright: ignore[reportPrivateUsage]",
    ) == [
        lsr.Finding(
            "larch/mod.py",
            lsr.KIND_PYRIGHT_IGNORE,
            "pyright: ignore[reportPrivateUsage]",
            1,
            3,
        )
    ]


def test_comma_separated_pyright_report_clauses_are_scanned_as_one_suppression(tmp_path: Path) -> None:
    assert _scan_comment(
        tmp_path,
        "# pyright: reportMissingImports=false, reportPrivateUsage=false",
    ) == [
        lsr.Finding(
            "larch/mod.py",
            lsr.KIND_PYRIGHT_REPORT,
            "pyright: reportMissingImports=false, reportPrivateUsage=false",
            1,
            3,
        ),
    ]


def test_baseline_row_suppresses_comma_separated_pyright_report_live_finding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_project(
        tmp_path,
        files={"larch/mod.py": _module("# pyright: reportMissingImports=false, reportPrivateUsage=false")},
        baseline=[
            _record(
                suppression_kind=lsr.KIND_PYRIGHT_REPORT,
                text="pyright: reportMissingImports=false, reportPrivateUsage=false",
            )
        ],
    )

    assert lsr.main(["--root", str(tmp_path)]) == 0
    assert "matching baseline finding" in capsys.readouterr().err


def test_plain_comments_containing_suppression_words_are_ignored(tmp_path: Path) -> None:
    assert not _scan_comment(tmp_path, "# this comment explains why noqa exists")


def test_semicolon_suppression_inside_comment_token_is_detected(tmp_path: Path) -> None:
    assert _scan_comment(tmp_path, "# formatter note; noqa") == [
        lsr.Finding("larch/mod.py", lsr.KIND_NOQA, "noqa", 1, 3)
    ]


def test_scope_excludes_tests_helpers_cache_vendor_and_virtualenv_dirs(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    for relpath in [
        "test_top.py",
        "larch/test_mod.py",
        "larch/pkg/test_nested.py",
        "larch/pkg/conftest.py",
        "larch/pkg/test_support.py",
        "larch/pkg/review_test_support.py",
        "larch/pkg/tests/helper.py",
        "larch/pkg/__pycache__/generated.py",
        "larch/pkg/.venv/vendor.py",
        "larch/pkg/vendor/generated.py",
        "pytest_sharding.py",
        "larch/core/config.py",
        "larch/core/proc.py",
    ]:
        path = python_dir / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text("VALUE = 1  # noqa\n", encoding="utf-8")

    assert [path.relative_to(python_dir).as_posix() for path in lsr.iter_source_files(python_dir)] == [
        "larch/core/config.py",
        "larch/core/proc.py",
        "pytest_sharding.py",
    ]


def test_unbaselined_suppression_exits_1(tmp_path: Path) -> None:
    _write_project(tmp_path, files={"larch/mod.py": _module("# noqa")}, baseline=[])

    assert lsr.main(["--root", str(tmp_path)]) == 1


def test_baseline_row_suppresses_live_finding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_project(tmp_path, files={"larch/mod.py": _module("# noqa")}, baseline=[_record()])

    assert lsr.main(["--root", str(tmp_path)]) == 0
    assert "matching baseline finding" in capsys.readouterr().err


def test_stale_baseline_row_exits_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_project(tmp_path, files={"larch/mod.py": "VALUE = 1\n"}, baseline=[_record()])

    assert lsr.main(["--root", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "stale baseline row: larch/mod.py" in err
    assert "suppression_kind=noqa" in err


@pytest.mark.parametrize(
    "baseline",
    [
        [_record(reason="")],
        [{"file": "larch/mod.py", "suppression_kind": lsr.KIND_NOQA, "text": "noqa", "occurrence": 1}],
        [_record(extra="bad")],
        [_record(file="python/larch/mod.py")],
        [_record(file="../escape.py")],
        [_record(text="")],
        [_record(occurrence=0)],
        [_record(occurrence=True)],
    ],
)
def test_malformed_baseline_rows_exit_2(tmp_path: Path, baseline: object) -> None:
    _write_project(tmp_path, files={"larch/mod.py": _module("# noqa")}, baseline=baseline)

    assert lsr.main(["--root", str(tmp_path)]) == 2


def test_duplicate_baseline_identity_exits_2(tmp_path: Path) -> None:
    row = _record()
    _write_project(tmp_path, files={"larch/mod.py": _module("# noqa")}, baseline=[row, row])

    assert lsr.main(["--root", str(tmp_path)]) == 2


def test_write_with_initial_reason_writes_canonical_json(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/second.py": _module("# type: ignore"),
            "pytest_sharding.py": _module("# noqa"),
        },
    )

    assert lsr.main(["--root", str(tmp_path), "--write", "--initial-reason", "bootstrap"]) == 0
    rows = json.loads((tmp_path / "python" / lsr.BASELINE_FILENAME).read_text(encoding="utf-8"))
    assert rows == [
        _record(file="larch/second.py", suppression_kind=lsr.KIND_TYPE_IGNORE, text="type: ignore", reason="bootstrap"),
        _record(file="pytest_sharding.py", reason="bootstrap"),
    ]


def test_routine_write_preserves_reasons(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={"larch/mod.py": _module("# noqa")},
        baseline=[_record(reason="preserved")],
    )

    assert lsr.main(["--root", str(tmp_path), "--write"]) == 0
    rows = json.loads((tmp_path / "python" / lsr.BASELINE_FILENAME).read_text(encoding="utf-8"))
    assert rows == [_record(reason="preserved")]


def test_routine_write_fails_when_new_live_finding_lacks_preserved_reason(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={"larch/mod.py": _module("# noqa\nVALUE2 = 2  # type: ignore")},
        baseline=[_record()],
    )

    assert lsr.main(["--root", str(tmp_path), "--write"]) == 2


def test_routine_write_initial_reason_does_not_seed_existing_baseline(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={"larch/mod.py": _module("# noqa\nVALUE2 = 2  # type: ignore")},
        baseline=[_record()],
    )

    assert lsr.main(["--root", str(tmp_path), "--write", "--initial-reason", "bootstrap"]) == 2


def test_write_preserves_reasons_and_shrinks_obsolete_rows(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={"larch/mod.py": _module("# noqa")},
        baseline=[_record(reason="kept"), _record(text="ruff: noqa", suppression_kind=lsr.KIND_RUFF_NOQA, reason="obsolete")],
    )

    assert lsr.main(["--root", str(tmp_path), "--write"]) == 0
    rows = json.loads((tmp_path / "python" / lsr.BASELINE_FILENAME).read_text(encoding="utf-8"))
    assert rows == [_record(reason="kept")]


def test_missing_baseline_in_check_mode_exits_2(tmp_path: Path) -> None:
    _write_project(tmp_path, files={"larch/mod.py": _module("# noqa")}, baseline=None)

    assert lsr.main(["--root", str(tmp_path)]) == 2


def test_non_utf8_source_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    python_dir = tmp_path / "python"
    path = python_dir / "larch" / "mod.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_bytes(b"\xff\xfe")
    _ = (python_dir / lsr.BASELINE_FILENAME).write_text("[]", encoding="utf-8")
    _git_init(tmp_path)

    assert lsr.main(["--root", str(tmp_path)]) == 2
    assert "UTF-8" in capsys.readouterr().err


def test_tokenization_error_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_project(tmp_path, files={"larch/mod.py": "VALUE = (\n"}, baseline=[])

    assert lsr.main(["--root", str(tmp_path)]) == 2
    assert "cannot parse source" in capsys.readouterr().err


def test_write_errors_are_reported_as_baseline_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_project(tmp_path, files={"larch/mod.py": "VALUE = 1\n"}, baseline=None)
    baseline_path = tmp_path / "python" / lsr.BASELINE_FILENAME
    baseline_path.mkdir()

    assert lsr.main(["--root", str(tmp_path), "--write"]) == 2
    assert "baseline path is not a regular file" in capsys.readouterr().err
